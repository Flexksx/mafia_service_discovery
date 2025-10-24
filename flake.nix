# flake.nix
{
  description = "Development environment for the Python Monolith Exam App";

  inputs = {
    nixpkgs.url = "github:NixOS/nixpkgs/nixos-unstable";
    flake-utils.url = "github:numtide/flake-utils";
  };

  outputs =
    {
      self,
      nixpkgs,
      flake-utils,
    }:
    flake-utils.lib.eachDefaultSystem (
      system:
      let
        pythonVersion = "python312";
        projectName = "artificial_intelligence_labs";

        pkgs = (
          import nixpkgs {
            inherit system;
            config = {
              allowUnfree = true;
            };
          }
        );

        systemDeps = with pkgs; [
          # Core build tools
          pkg-config
          gcc
          gcc.cc.lib
          zlib

          postgresql.lib

          ngrok

          # Example: If you need other common libs
          # openssl
          # zlib
          # sqlite

        ];

        pythonEnv = pkgs.${pythonVersion};
        poetry = pkgs.poetry;

      in
      {
        # --- Development Shell ---
        # Access with `nix develop`
        devShells.default = pkgs.mkShell {
          name = "${projectName}-env";

          # Packages available in the shell
          packages = [
            pythonEnv # Provides the `python` command
            poetry # Provides the `poetry` command
          ]
          ++ systemDeps;

          # Environment variables and commands to run when entering the shell
          shellHook = ''
            echo "Entering ${projectName} development environment..."

            # Recommended: Configure Poetry to create the virtualenv inside the project directory (.venv)
            # This makes it easier for IDEs and tools to find it.
            export POETRY_VIRTUALENVS_IN_PROJECT=true
            export LD_LIBRARY_PATH="${pkgs.gcc.cc.lib}/lib:${pkgs.zlib}/lib:$LD_LIBRARY_PATH"


            # Optional: Automatically run 'poetry install' if needed
            # This checks if the venv exists and if poetry.lock is newer than the venv marker.
            # Remove or comment this out if you prefer running 'poetry install' manually.
            # Note: This might run 'poetry install' more often than strictly necessary on minor changes,
            # but ensures consistency when entering the shell.
            if [ ! -d ".venv" ] || [ "poetry.lock" -nt ".venv" ]; then
              echo "Running 'poetry install --sync' to set up/update virtual environment..."
              # --sync removes packages not in the lock file - good for consistency
              # --no-root prevents installing the project itself in editable mode into the venv,
              # which is often the desired behavior for applications.
              poetry install --sync --no-root
            else
              echo "Poetry virtual environment (.venv) seems up-to-date."
            fi

            # You can add other exports here if needed
            # export DATABASE_URL="postgresql://user:pass@host:port/db"

            echo "Ready! Use 'poetry run ...' or activate with 'poetry shell'."
          '';
        };

      }
    );
}
