# Explicit allowlists: never assemble instructions by globbing this directory.
# Home base and Samov's overlay load separately; home is their composed test view.
let
  merge = files: builtins.concatStringsSep "\n" (map builtins.readFile files);
  homeBase = merge [
    ./AGENTS.common.md
    ./AGENTS.home.md
  ];
  homePersonal = merge [
    ./AGENTS.md
    ./AGENTS.review.md
  ];
in
{
  inherit homeBase homePersonal;
  home = homeBase + "\n" + homePersonal;
  corporate = merge [
    ./AGENTS.common.md
    ./AGENTS.corporate.md
  ];
  corporatePersonal = merge [
    ./AGENTS.md
    ./AGENTS.corporate-personal.md
  ];
}
