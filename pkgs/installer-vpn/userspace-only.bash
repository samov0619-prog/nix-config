# Installer-only override at upstream's documented function override point.
# Never select an absent or older AmneziaWG kernel module from the live ISO.
add_if() {
    cmd "$WG_QUICK_USERSPACE_IMPLEMENTATION" "$INTERFACE"
}
