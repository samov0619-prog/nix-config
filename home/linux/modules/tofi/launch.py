"""Parse Tofi's command with GLib, then hand argv to UWSM without a shell."""

import argparse
import ctypes
import os
import subprocess
import sys


def parse_command(command, library):
    if b"\0" in command:
        raise ValueError("NUL in launcher output")
    glib = ctypes.CDLL(library)
    string_array = ctypes.POINTER(ctypes.c_char_p)
    glib.g_shell_parse_argv.argtypes = [
        ctypes.c_char_p,
        ctypes.POINTER(ctypes.c_int),
        ctypes.POINTER(string_array),
        ctypes.POINTER(ctypes.c_void_p),
    ]
    glib.g_shell_parse_argv.restype = ctypes.c_int
    glib.g_strfreev.argtypes = [string_array]
    glib.g_strfreev.restype = None
    glib.g_error_free.argtypes = [ctypes.c_void_p]
    glib.g_error_free.restype = None
    count = ctypes.c_int()
    arguments = string_array()
    error = ctypes.c_void_p()
    if not glib.g_shell_parse_argv(
        command, ctypes.byref(count), ctypes.byref(arguments), ctypes.byref(error)
    ):
        if error:
            glib.g_error_free(error)
        raise ValueError("Invalid launcher command quoting")
    try:
        result = [arguments[index] for index in range(count.value)]
    finally:
        glib.g_strfreev(arguments)
    if not result or not result[0]:
        raise ValueError("Empty launcher executable")
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--glib", required=True)
    parser.add_argument("--tofi", required=True)
    parser.add_argument("--uwsm", required=True)
    options = parser.parse_args()
    try:
        selection = subprocess.run(
            [options.tofi, "--drun-launch=false"], stdout=subprocess.PIPE
        )
        if selection.returncode != 0 or not selection.stdout.strip():
            return 0
        arguments = parse_command(selection.stdout, options.glib)
        os.execv(
            options.uwsm,
            [os.fsencode(options.uwsm), b"app", b"--", *arguments],
        )
    except (OSError, ValueError) as error:
        print(f"tofi-launch: {error}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
