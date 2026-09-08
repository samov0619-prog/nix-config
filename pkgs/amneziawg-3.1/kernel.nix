{
  lib,
  stdenv,
  fetchFromGitHub,
  kernel,
  kernelModuleMakeFlags,
}:
stdenv.mkDerivation (finalAttrs: {
  pname = "amneziawg";
  version = "3.1.20260812";

  src = fetchFromGitHub {
    owner = "amnezia-vpn";
    repo = "amneziawg-linux-kernel-module";
    rev = "46803204e7ec3b068199cd671143bec661d3fe21";
    hash = "sha256-dJ7Au4J8iPlphSzTa3Gol/LMlroroSc2IUmXZfjA0k8=";
  };

  sourceRoot = "${finalAttrs.src.name}/src";
  hardeningDisable = [ "pic" ];
  nativeBuildInputs = kernel.moduleBuildDependencies;
  buildFlags = [ "module" ];
  makeFlags = kernelModuleMakeFlags ++ [
    "KERNELDIR=${kernel.dev}/lib/modules/${kernel.modDirVersion}/build"
  ];
  installFlags = [
    "DEPMOD=true"
    "INSTALL_MOD_PATH=${placeholder "out"}"
  ];

  meta = {
    description = "AmneziaWG 3.1 kernel module";
    homepage = "https://amnezia.org";
    license = lib.licenses.gpl2Only;
    platforms = lib.platforms.linux;
  };
})
