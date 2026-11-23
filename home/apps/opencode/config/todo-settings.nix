{ todoDirectory }:
let
  tools = [
    "agent_todo_read"
    "agent_todo_propose"
  ];
  toolRules =
    effect:
    map (action: {
      inherit action effect;
      resource = "*";
    }) tools;
in
{
  # Native tool snapshots omit fully denied actions, including their schemas.
  permissions = toolRules "deny";
  agents = builtins.listToAttrs (
    map
      (name: {
        inherit name;
        value.permissions =
          toolRules "allow"
          ++
            map
              (resource: {
                action = "read";
                inherit resource;
                effect = "allow";
              })
              [
                todoDirectory
                "${todoDirectory}/*"
              ];
      })
      [
        "build"
        "plan"
      ]
  );
}
