use super::*;
use std::io::Write;
use std::time::Duration;

// The real Unix socket reports EOF once. Fail on a second read so the broken
// upstream loop cannot spin, allocate indefinitely, or hang the test suite.
struct EofGuard {
    stream: UnixStream,
    eof: bool,
}

impl Read for EofGuard {
    fn read(&mut self, buffer: &mut [u8]) -> io::Result<usize> {
        assert!(!self.eof, "event reader continued reading after EOF");
        let count = self.stream.read(buffer)?;
        self.eof = count == 0 && !buffer.is_empty();
        Ok(count)
    }
}

fn input(bytes: &[u8]) -> EofGuard {
    let (mut sender, receiver) = UnixStream::pair().unwrap();
    receiver
        .set_read_timeout(Some(Duration::from_secs(1)))
        .unwrap();
    sender.write_all(bytes).unwrap();
    drop(sender);
    EofGuard {
        stream: receiver,
        eof: false,
    }
}

fn assert_unexpected_eof(bytes: &[u8]) {
    let error = App::get_event(&mut input(bytes)).unwrap_err();
    assert!(
        matches!(error, AppError::IOError(ref inner) if inner.kind() == io::ErrorKind::UnexpectedEof),
        "expected UnexpectedEof, got {error:?}"
    );
}

#[test]
fn preserves_frames_and_utf8() {
    let mut socket = input("windowtitle>>пример 🙂\nbell>>abc\n".as_bytes());
    assert_eq!(App::get_event(&mut socket).unwrap(), "windowtitle>>пример 🙂");
    assert_eq!(App::get_event(&mut socket).unwrap(), "bell>>abc");
}

#[test]
fn eof_before_event() {
    assert_unexpected_eof(b"");
}

#[test]
fn eof_mid_event() {
    assert_unexpected_eof(b"bell>>abc");
}

#[test]
fn eof_mid_utf8_character() {
    assert_unexpected_eof(&[0xc3]);
}
