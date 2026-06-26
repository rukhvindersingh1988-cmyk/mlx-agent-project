# Google Project IDX Environment Configuration
{ pkgs, ... }: {
  channel = "stable-23.11";
  packages = [
    pkgs.curl
    pkgs.git
    pkgs.jq
    pkgs.openssl
    pkgs.python312
    pkgs.python312Packages.pip
    pkgs.python312Packages.virtualenv
    pkgs.ruff
  ];
  env = {};
  idx = {
    extensions = ["google.gemini-code-assist"];
    workspace = {
      onCreate = {
        setup = "echo 'Antigravity Environment Ready'";
      };
    };
  };
}
