{ lib }:
let
  fixturePkgs = {
    fetchurl = _: "/fixture/download.jar";
    writeShellScript = _: text: text;
    python3 = "/fixture/python";
    rclone = "/fixture/rclone";
    packwiz = "/fixture/packwiz";
    jdk_headless = "/fixture/java";
    curl = "/fixture/curl";
  };
  evaluate =
    instance:
    (lib.evalModules {
      specialArgs.pkgs = fixturePkgs;
      modules = [
        ../default.nix
        {
          options.systemd = lib.mkOption {
            type = lib.types.attrs;
            default = { };
          };
          config.minecraft.server = instance;
        }
      ];
    }).config;
  instance = {
    serverDir = "/fixture/server with 'quote";
    packwizDir = "/fixture/packwiz";
  };
  inactive = evaluate null;
  manual = evaluate instance;
  automatic = evaluate (instance // { autoStart = true; });
  units = manual.systemd.user;
  serve = units.services.packwiz-serve;
  update = units.services.minecraft-packwiz-update;
  server = units.services.minecraft-server;
  watcher = units.paths.ftb-backups-fabric-1214;
  backup = units.services.ftb-backups-fabric-1214;
  readiness = serve.Service.ExecStartPost;
in
assert inactive.systemd == { };
assert manual.minecraft.server.memory == "20G";
assert manual.minecraft.server.autoStart == false;
assert units.targets.minecraft.Install.WantedBy == [ ];
assert automatic.systemd.user.targets.minecraft.Install.WantedBy == [ "default.target" ];
assert automatic.systemd.user.services == units.services;
assert automatic.systemd.user.paths == units.paths;
assert lib.all
  (
    service:
    service.Unit.PartOf == [ "minecraft.target" ] && service.Install.WantedBy == [ "minecraft.target" ]
  )
  [
    serve
    update
    server
  ];
assert serve.Service.Type == "exec";
assert serve.Service.TimeoutStartSec == "40s";
assert serve.Service.RestartSec == "5s";
assert lib.hasPrefix "/fixture/curl/bin/curl --disable " readiness;
assert lib.all (flag: lib.hasInfix flag readiness) [
  "--disable"
  "--fail"
  "--noproxy '*'"
  "--retry 30"
  "--retry-delay 1"
  "--retry-max-time 30"
  "--retry-connrefused"
  "--retry-all-errors"
  "--max-time 1"
  "http://127.0.0.1:8180/pack.toml"
];
assert update.Service.Type == "oneshot";
assert update.Service.RemainAfterExit;
assert update.Unit.After == [ "packwiz-serve.service" ];
assert update.Unit.Requires == [ "packwiz-serve.service" ];
assert lib.hasInfix "http://127.0.0.1:8180/pack.toml" update.Service.ExecStart;
assert server.Unit.After == [ "minecraft-packwiz-update.service" ];
assert server.Unit.Requires == [ "minecraft-packwiz-update.service" ];
assert watcher.Path.PathChanged == "${instance.serverDir}/backups/backups.json";
assert watcher.Install.WantedBy == [ "default.target" ];
assert !(watcher.Unit ? PartOf);
assert !(backup.Unit ? PartOf);
assert backup.Service.Type == "oneshot";
assert lib.hasInfix "/fixture/python/bin/python3" backup.Service.ExecStart;
assert lib.hasInfix "backup-sync.py" backup.Service.ExecStart;
assert lib.hasInfix (lib.escapeShellArg "${instance.serverDir}/backups") backup.Service.ExecStart;
assert lib.hasInfix "gd-backups:minecraft_backups_fabric_1.21.4" backup.Service.ExecStart;
assert lib.hasInfix "--rclone /fixture/rclone/bin/rclone" backup.Service.ExecStart;
{
  checks = {
    inactiveHasNoUnits = true;
    manualByDefaultAndAutostartOptIn = true;
    targetLifecyclePropagation = true;
    updateRemainsActive = true;
    boundedHttpReadiness = true;
    backupRemainsIndependent = true;
    backupWrapperAndWatcherPreserved = true;
    fixturePackagesOnly = true;
  };
  # Available to local HTTP/systemd fixture checks without building any packages.
  lifecycleUnits = {
    minecraft = units.targets.minecraft;
    packwiz-serve = serve;
    minecraft-packwiz-update = update;
    minecraft-server = server;
  };
}
