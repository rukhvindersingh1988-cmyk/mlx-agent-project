# 🧠 Codebase Guide: uv
**Source Repository:** https://github.com/astral-sh/uv
**Ingested At:** 2026-06-29 01:58:27

## 📁 Project Structure
```text
- _typos.toml
- Cargo.toml
- LICENSE-APACHE
- dist-workspace.toml
- mkdocs.yml
- rustfmt.toml
- uv.lock
- CHANGELOG.md
- .pre-commit-config.yaml
- Dockerfile
- BENCHMARKS.md
- .known-crates
- pyproject.toml
- Cargo.lock
- .ignore
- .prettierignore
- .editorconfig
- README.md
- .gitignore
- STYLE.md
- CONTRIBUTING.md
- ruff.toml
- .prettierrc
- .gitattributes
- clippy.toml
- rust-toolchain.toml
- AGENTS.md
- uv.schema.json
- .python-versions
- CLAUDE.md
- SECURITY.md
- LICENSE-MIT
- .config/nextest.toml
- crates/README.md
- crates/uv-auth/Cargo.toml
- crates/uv-auth/README.md
- crates/uv-auth/src/cache.rs
- crates/uv-auth/src/pyx.rs
- crates/uv-auth/src/credentials.rs
- crates/uv-auth/src/lib.rs
- crates/uv-auth/src/index.rs
- crates/uv-auth/src/store.rs
- crates/uv-auth/src/service.rs
- crates/uv-auth/src/access_token.rs
- crates/uv-auth/src/middleware.rs
- crates/uv-auth/src/realm.rs
- crates/uv-auth/src/providers.rs
- crates/uv-auth/src/keyring.rs
- crates/uv-keyring/Cargo.toml
- crates/uv-keyring/README.md
- crates/uv-keyring/tests/threading.rs
- crates/uv-keyring/tests/basic.rs
- crates/uv-keyring/tests/common/mod.rs
- crates/uv-keyring/src/secret_service.rs
- crates/uv-keyring/src/error.rs
- crates/uv-keyring/src/macos.rs
- crates/uv-keyring/src/lib.rs
- crates/uv-keyring/src/credential.rs
- crates/uv-keyring/src/mock.rs
- crates/uv-keyring/src/windows.rs
- crates/uv-keyring/src/blocking.rs
- crates/uv-requirements/Cargo.toml
- crates/uv-requirements/README.md
- crates/uv-requirements/src/upgrade.rs
- crates/uv-requirements/src/lib.rs
- crates/uv-requirements/src/extras.rs
- crates/uv-requirements/src/source_tree.rs
- crates/uv-requirements/src/unnamed.rs
- crates/uv-requirements/src/lookahead.rs
- crates/uv-requirements/src/specification.rs
- crates/uv-requirements/src/sources.rs
- crates/uv-git-types/Cargo.toml
- crates/uv-git-types/README.md
- crates/uv-git-types/src/lib.rs
- crates/uv-git-types/src/oid.rs
- crates/uv-git-types/src/github.rs
- crates/uv-git-types/src/reference.rs
- crates/uv-platform-tags/Cargo.toml
- crates/uv-platform-tags/README.md
- crates/uv-platform-tags/src/platform_tag.rs
- crates/uv-platform-tags/src/lib.rs
- crates/uv-platform-tags/src/tags.rs
- crates/uv-platform-tags/src/abi_tag.rs
- crates/uv-platform-tags/src/platform.rs
- crates/uv-platform-tags/src/language_tag.rs
- crates/uv-cache-key/Cargo.toml
- crates/uv-cache-key/README.md
- crates/uv-cache-key/src/canonical_url.rs
- crates/uv-cache-key/src/lib.rs
- crates/uv-cache-key/src/cache_key.rs
- crates/uv-cache-key/src/digest.rs
- crates/uv-platform/Cargo.toml
- crates/uv-platform/README.md
- crates/uv-platform/src/libc.rs
- crates/uv-platform/src/os.rs
- crates/uv-platform/src/arch.rs
- crates/uv-platform/src/host.rs
- crates/uv-platform/src/lib.rs
- crates/uv-platform/src/cpuinfo.rs
- crates/uv-scripts/Cargo.toml
- ... (1345 more files)
```

## 📄 Core Code & APIs

### File: `.pre-commit-config.yaml`

```
fail_fast: true

exclude: |
  (?x)^(
    .*/(snapshots)/.*|
  )$

repos:
  - repo: https://github.com/abravalheri/validate-pyproject
    rev: v0.24.1
    hooks:
      - id: validate-pyproject

  - repo: https://github.com/crate-ci/typos
    rev: v1.42.3
    hooks:
      - id: typos

  - repo: local
    hooks:
      - id: rustfmt
        name: rustfmt
        entry: rustfmt
        language: system
        types: [rust]

  - repo: local
    hooks:
      - id: cargo-dev-generate-all
        name: cargo dev generate-all
        entry: cargo dev generate-all
        language: system
        types: [rust]
        pass_filenames: false
        files: ^crates/(uv-cli|uv-settings)/

  - repo: local
    hooks:
      - id: prettier
        name: prettier
        entry: prettier --write --ignore-unknown
        language: node
        additional_dependencies: ["prettier@3"]
        types_or: [yaml, json5]

  - repo: https://github.com/astral-sh/ruff-pre-commit
    rev: v0.14.14
    hooks:
      - id: ruff-format
      - id: ruff
        args: [--fix, --exit-non-zero-on-fix]
```

### File: `README.md`

```
# uv

[![uv](https://img.shields.io/endpoint?url=https://raw.githubusercontent.com/astral-sh/uv/main/assets/badge/v0.json)](https://github.com/astral-sh/uv)
[![image](https://img.shields.io/pypi/v/uv.svg)](https://pypi.python.org/pypi/uv)
[![image](https://img.shields.io/pypi/l/uv.svg)](https://pypi.python.org/pypi/uv)
[![image](https://img.shields.io/pypi/pyversions/uv.svg)](https://pypi.python.org/pypi/uv)
[![Actions status](https://github.com/astral-sh/uv/actions/workflows/ci.yml/badge.svg)](https://github.com/astral-sh/uv/actions)
[![Discord](https://img.shields.io/badge/Discord-%235865F2.svg?logo=discord&logoColor=white)](https://discord.gg/astral-sh)

An extremely fast Python package and project manager, written in Rust.

<p align="center">
  <picture align="center">
    <source media="(prefers-color-scheme: dark)" srcset="https://github.com/astral-sh/uv/assets/1309177/03aa9163-1c79-4a87-a31d-7a9311ed9310">
    <source media="(prefers-color-scheme: light)" srcset="https://github.com/astral-sh/uv/assets/1309177/629e59c0-9c6e-4013-9ad4-adb2bcf5080d">
    <img alt="Shows a bar chart with benchmark results." src="https://github.com/astral-sh/uv/assets/1309177/629e59c0-9c6e-4013-9ad4-adb2bcf5080d">
  </picture>
</p>

<p align="center">
  <i>Installing <a href="https://trio.readthedocs.io/">Trio</a>'s dependencies with a warm cache.</i>
</p>

## Highlights

- A single tool to replace `pip`, `pip-tools`, `pipx`, `poetry`, `pyenv`, `twine`, `virtualenv`, and
  more.
- [10-100x faster](https://github.com/astral-sh/uv/blob/main/BENCHMARKS.md) than `pip`.
- Provides [comprehensive project management](#projects), with a
  [universal lockfile](https://docs.astral.sh/uv/concepts/projects/layout#the-lockfile).
- [Runs scripts](#scripts), with support for
  [inline dependency metadata](https://docs.astral.sh/uv/guides/scripts#declaring-script-dependencies).
- [Installs and manages](#python-versions) Python versions.
- [Runs and installs](#tools) tools published as Python packages.
- Includes a [pip-compatible interface](#the-pip-interface) for a performance boost with a familiar
  CLI.
- Supports Cargo-style [workspaces](https://docs.astral.sh/uv/concepts/projects/workspaces) for
  scalable projects.
- Disk-space efficient, with a [global cache](https://docs.astral.sh/uv/concepts/cache) for
  dependency deduplication.
- Installable without Rust or Python via `curl` or `pip`.
- Supports macOS, Linux, and Windows.

uv is backed by [Astral](https://astral.sh), the creators of
[Ruff](https://github.com/astral-sh/ruff) and [ty](https://github.com/astral-sh/ty).

## Installation

Install uv with our standalone installers:

```bash
# On macOS and Linux.
curl -LsSf https://astral.sh/uv/install.sh | sh
```

```bash
# On Windows.
powershell -ExecutionPolicy ByPass -c "irm https://astral.sh/uv/install.ps1 | iex"
```

Or, from [PyPI](https://pypi.org/project/uv/):

```bash
# With pip.
pip install uv
```

```bash
# Or pipx.
pipx install uv
```

If installed via the standalone installer, uv can update itself to the latest version:

```bash
uv self update
```

See the [installation documentation](https://docs.astral.sh/uv/getting-started/installation/) for
details and alternative installation methods.

## Documentation

uv's documentation is available at [docs.astral.sh/uv](https://docs.astral.sh/uv).

Additionally, the command line reference documentation can be viewed with `uv help`.

## Features

### Projects

uv manages project dependencies and environments, with support for lockfiles, workspaces, and more,
similar to `rye` or `poetry`:

```console
$ uv init example
Initialized project `example` at `/home/user/example`

$ cd example

$ uv add ruff
Creating virtual environment at: .venv
Resolved 2 packages in 170ms
   Built example @ file:///home/user/example
Prepared 2 packages in 627ms
Installed 2 packages in 1ms
 + example==0.1.0 (from file:///home/user/example)
 + ruff==0.5.0

$ uv run ruff check
All checks passed!

$ uv lock
Resolved 2 packages in 0.33ms

$ uv sync
Resolved 2 packages in 0.70ms
Checked 1 package in 0.02ms
```

... (truncated)
```

### File: `AGENTS.md`

```
- Read CONTRIBUTING.md for guidelines on how to run tools
- ALWAYS attempt to add a test case for changed behavior
- PREFER integration tests, e.g., at `it/...` over unit tests
- PREFER `insta` snapshots following patterns in nearby tests over substring assertions
- When making changes for Windows from Unix, use `cargo xwin clippy` to check compilation
- NEVER perform builds with the release profile, unless asked or reproducing performance issues
- PREFER running specific tests over running the entire test suite
- AVOID using `panic!`, `unreachable!`, `.unwrap()`, unsafe code, and clippy rule ignores
- PREFER patterns like `if let` to handle fallibility
- ALWAYS write `SAFETY` comments following our usual style when writing `unsafe` code
- PREFER `#[expect()]` over `[allow()]` if clippy must be disabled
- PREFER let chains (`if let` combined with `&&`) over nested `if let` statements
- NEVER update all dependencies in the lockfile and ALWAYS use `cargo update --precise` to make
  lockfile changes
- NEVER assume clippy warnings are pre-existing, it is very rare that `main` has warnings
- ALWAYS read and copy the style of similar tests when adding new cases
- PREFER top-level imports over local imports or fully qualified names
- AVOID shortening variable names, e.g., use `version` instead of `ver`, and `requires_python`
  instead of `rp`
- PREFER [`TypeName`] references when writing Rust doc comments
```

### File: `crates/README.md`

```
# Crates

## [uv-bench](./uv-bench)

Functionality for benchmarking uv.

## [uv-cache-key](./uv-cache-key)

Generic functionality for caching paths, URLs, and other resources across platforms.

## [uv-distribution-filename](./uv-distribution-filename)

Parse built distribution (wheel) and source distribution (sdist) filenames to extract structured
metadata.

## [uv-distribution-types](./uv-distribution-types)

Abstractions for representing built distributions (wheels) and source distributions (sdists), and
the sources from which they can be downloaded.

## [uv-install-wheel-rs](./uv-install-wheel)

Install built distributions (wheels) into a virtual environment.

## [uv-once-map](./uv-once-map)

A [`waitmap`](https://github.com/withoutboats/waitmap)-like concurrent hash map for executing tasks
exactly once.

## [uv-pep440-rs](./uv-pep440)

Utilities for interacting with Python version numbers and specifiers.

## [uv-pep508-rs](./uv-pep508)

Utilities for parsing and evaluating
[dependency specifiers](https://packaging.python.org/en/latest/specifications/dependency-specifiers/),
previously known as [PEP 508](https://peps.python.org/pep-0508/).

## [uv-platform-tags](./uv-platform-tags)

Functionality for parsing and inferring Python platform tags as per
[PEP 425](https://peps.python.org/pep-0425/).

## [uv-cli](./uv-cli)

Command-line interface for the uv package manager.

## [uv-build-frontend](./uv-build-frontend)

A [PEP 517](https://www.python.org/dev/peps/pep-0517/)-compatible build frontend for uv.

## [uv-cache](./uv-cache)

Functionality for caching Python packages and associated metadata.

## [uv-client](./uv-client)

Client for interacting with PyPI-compatible HTTP APIs.

## [uv-dev](./uv-dev)

Development utilities for uv.

## [uv-dispatch](./uv-dispatch)

A centralized `struct` for resolving and building source distributions in isolated environments.
Implements the traits defined in `uv-types`.

## [uv-distribution](./uv-distribution)

Client for interacting with built distributions (wheels) and source distributions (sdists). Capable
of fetching metadata, distribution contents, etc.

## [uv-extract](./uv-extract)

Utilities for extracting files from archives.

## [uv-fs](./uv-fs)

Utilities for interacting with the filesystem.

## [uv-git](./uv-git)

Functionality for interacting with Git repositories.

## [uv-installer](./uv-installer)

Functionality for installing Python packages into a virtual environment.

## [uv-python](./uv-python)

Functionality for detecting and leveraging the current Python interpreter.

## [uv-netrc](./uv-netrc)

A vendored netrc parser for uv.

## [uv-normalize](./uv-normalize)

Normalize package and extra names as per Python specifications.

## [uv-requirements](./uv-requirements)

Utilities for reading package requirements from `pyproject.toml` and `requirements.txt` files.

## [uv-resolver](./uv-resolver)

Functionality for resolving Python packages and their dependencies.

## [uv-shell](./uv-shell)

Utilities for detecting and manipulating shell environments.

## [uv-types](./uv-types)

Shared traits for uv, to avoid circular dependencies.

## [uv-pypi-types](./uv-pypi-types)

... (truncated)
```

### File: `crates/uv-auth/README.md`

```
<!-- This file is generated. DO NOT EDIT -->

# uv-auth

This crate is an internal component of [uv](https://crates.io/crates/uv). The Rust API exposed here
is unstable and will have frequent breaking changes.

This version (0.0.58) is a component of [uv 0.11.25](https://crates.io/crates/uv/0.11.25). The
source can be found [here](https://github.com/astral-sh/uv/blob/0.11.25/crates/uv-auth).

See uv's
[crate versioning policy](https://docs.astral.sh/uv/reference/policies/versioning/#crate-versioning)
for details on versioning.
```

### File: `crates/uv-auth/src/index.rs`

```rust
use std::fmt::{self, Display, Formatter};

use rustc_hash::FxHashSet;
use url::Url;
use uv_redacted::DisplaySafeUrl;

/// When to use authentication.
#[derive(
    Copy,
    Clone,
    Debug,
    Default,
    Hash,
    Eq,
    PartialEq,
    Ord,
    PartialOrd,
    serde::Serialize,
    serde::Deserialize,
)]
#[serde(rename_all = "kebab-case")]
#[cfg_attr(feature = "schemars", derive(schemars::JsonSchema))]
pub enum AuthPolicy {
    /// Authenticate when necessary.
    ///
    /// If credentials are provided, they will be used. Otherwise, an unauthenticated request will
    /// be attempted first. If the request fails, uv will search for credentials. If credentials are
    /// found, an authenticated request will be attempted.
    #[default]
    Auto,
    /// Always authenticate.
    ///
    /// If credentials are not provided, uv will eagerly search for credentials. If credentials
    /// cannot be found, uv will error instead of attempting an unauthenticated request.
    Always,
    /// Never authenticate.
    ///
    /// If credentials are provided, uv will error. uv will not search for credentials.
    Never,
}

impl Display for AuthPolicy {
    fn fmt(&self, f: &mut Formatter) -> fmt::Result {
        match self {
            Self::Auto => write!(f, "auto"),
            Self::Always => write!(f, "always"),
            Self::Never => write!(f, "never"),
        }
    }
}

// TODO(john): We are not using `uv_distribution_types::Index` directly
// here because it would cause circular crate dependencies. However, this
// could potentially make sense for a future refactor.
#[derive(Debug, Clone, Hash, Eq, PartialEq)]
pub struct Index {
    pub url: DisplaySafeUrl,
    /// The root endpoint where authentication is applied.
    /// For PEP 503 endpoints, this excludes `/simple`.
    pub root_url: DisplaySafeUrl,
    pub auth_policy: AuthPolicy,
}

impl Index {
    fn is_prefix_for(&self, url: &Url) -> bool {
        if self.root_url.scheme() != url.scheme()
            || self.root_url.host_str() != url.host_str()
            || self.root_url.port_or_known_default() != url.port_or_known_default()
        {
            return false;
        }

        is_path_prefix(self.root_url.path(), url.path())
    }
}

/// Returns `true` if `prefix` is a complete path-segment prefix of `path`.
///
/// This rejects partial segment matches, so `/simple` matches `/simple/anyio` but not
/// `/simpleevil`.
pub(crate) fn is_path_prefix(prefix: &str, path: &str) -> bool {
    if prefix == path {
        return true;
    }

    let Some(suffix) = path.strip_prefix(prefix) else {
        return false;
    };

    prefix.ends_with('/') || suffix.starts_with('/')
}

// TODO(john): Multiple methods in this struct need to iterate over
// all the indexes in the set. There are probably not many URLs to
// iterate through, but we could use a trie instead of a HashSet here
// for more efficient search.
#[derive(Debug, Default, Clone, Eq, PartialEq)]
pub struct Indexes(FxHashSet<Index>);

impl Indexes {
    pub fn new() -> Self {
        Self(FxHashSet::default())
    }

    /// Create a new [`Indexes`] instance from an iterator of [`Index`]s.
    pub fn from_indexes(urls: impl IntoIterator<Item = Index>) -> Self {
        let mut index_urls = Self::new();
        for url in urls {
            index_urls.0.insert(url);
        }
        index_urls
    }

    /// Get the index for a URL if one exists.
    pub(crate) fn index_for(&self, url: &Url) -> Option<&Index> {
        self.find_prefix_index(url)
    }

    /// Get the [`AuthPolicy`] for a URL.
    pub(crate) fn auth_policy_for(&self, url: &Url) -> AuthPolicy {
... (truncated)
```

### File: `crates/uv-keyring/README.md`

```
# uv-keyring

This is vendored from [keyring-rs crate](https://github.com/open-source-cooperative/keyring-rs)
commit 9635a2f53a19eb7f188cdc4e38982dcb19caee00.

A cross-platform library to manage storage and retrieval of passwords (and other secrets) in the
underlying platform secure store, with a fully-developed example that provides a command-line
interface.

## Usage

You can use the `Entry::new` function to create a new keyring entry. The `new` function takes a
service name and a user's name which together identify the entry.

Passwords (strings) or secrets (binary data) can be added to an entry using its `set_password` or
`set_secret` methods, respectively. (These methods create or update an entry in the underlying
platform's persistent credential store.) The password or secret can then be read back using the
`get_password` or `get_secret` methods. The underlying credential (with its password/secret data)
can then be removed using the `delete_credential` method.

```rust
use uv_keyring::{Entry, Result};

#[tokio::main]
async fn main() -> Result<()> {
    let entry = Entry::new("my-service", "my-name")?;
    entry.set_password("topS3cr3tP4$$w0rd").await?;
    let password = entry.get_password().await?;
    println!("My password is '{}'", password);
    entry.delete_credential().await?;
    Ok(())
}
```

## Errors

Creating and operating on entries can yield a `keyring::Error` which provides both a
platform-independent code that classifies the error and, where relevant, underlying platform errors
or more information about what went wrong.

## Platforms

This crate provides built-in implementations of the following platform-specific credential stores:

- _Linux_, _FreeBSD_, _OpenBSD_: The DBus-based Secret Service.
- _macOS_: Keychain Services.
- _Windows_: The Windows Credential Manager.

It can be built and used on other platforms, but will not provide a built-in credential store
implementation; you will have to bring your own.

### Platform-specific issues

If you use the _Secret Service_ as your credential store, be aware that every call to the Secret
Service is done via an inter-process call, which takes time (typically tens if not hundreds of
milliseconds).

If you use the _Windows-native credential store_, be careful about multi-threaded access, because
the Windows credential store does not guarantee your calls will be serialized in the order they are
made. Always access any single credential from just one thread at a time, and if you are doing
operations on multiple credentials that require a particular serialization order, perform all those
operations from the same thread.

The _macOS credential store_ does not allow service names or usernames to be empty, because empty
fields are treated as wildcards on lookup. Use some default, non-empty value instead.
```

### File: `crates/uv-requirements/README.md`

```
<!-- This file is generated. DO NOT EDIT -->

# uv-requirements

This crate is an internal component of [uv](https://crates.io/crates/uv). The Rust API exposed here
is unstable and will have frequent breaking changes.

This version (0.0.58) is a component of [uv 0.11.25](https://crates.io/crates/uv/0.11.25). The
source can be found [here](https://github.com/astral-sh/uv/blob/0.11.25/crates/uv-requirements).

See uv's
[crate versioning policy](https://docs.astral.sh/uv/reference/policies/versioning/#crate-versioning)
for details on versioning.
```

### File: `crates/uv-git-types/README.md`

```
<!-- This file is generated. DO NOT EDIT -->

# uv-git-types

This crate is an internal component of [uv](https://crates.io/crates/uv). The Rust API exposed here
is unstable and will have frequent breaking changes.

This version (0.0.58) is a component of [uv 0.11.25](https://crates.io/crates/uv/0.11.25). The
source can be found [here](https://github.com/astral-sh/uv/blob/0.11.25/crates/uv-git-types).

See uv's
[crate versioning policy](https://docs.astral.sh/uv/reference/policies/versioning/#crate-versioning)
for details on versioning.
```

### File: `crates/uv-platform-tags/README.md`

```
<!-- This file is generated. DO NOT EDIT -->

# uv-platform-tags

This crate is an internal component of [uv](https://crates.io/crates/uv). The Rust API exposed here
is unstable and will have frequent breaking changes.

This version (0.0.58) is a component of [uv 0.11.25](https://crates.io/crates/uv/0.11.25). The
source can be found [here](https://github.com/astral-sh/uv/blob/0.11.25/crates/uv-platform-tags).

See uv's
[crate versioning policy](https://docs.astral.sh/uv/reference/policies/versioning/#crate-versioning)
for details on versioning.
```

### File: `crates/uv-cache-key/README.md`

```
<!-- This file is generated. DO NOT EDIT -->

# uv-cache-key

This crate is an internal component of [uv](https://crates.io/crates/uv). The Rust API exposed here
is unstable and will have frequent breaking changes.

This version (0.0.58) is a component of [uv 0.11.25](https://crates.io/crates/uv/0.11.25). The
source can be found [here](https://github.com/astral-sh/uv/blob/0.11.25/crates/uv-cache-key).

See uv's
[crate versioning policy](https://docs.astral.sh/uv/reference/policies/versioning/#crate-versioning)
for details on versioning.
```

### File: `crates/uv-platform/README.md`

```
<!-- This file is generated. DO NOT EDIT -->

# uv-platform

This crate is an internal component of [uv](https://crates.io/crates/uv). The Rust API exposed here
is unstable and will have frequent breaking changes.

This version (0.0.58) is a component of [uv 0.11.25](https://crates.io/crates/uv/0.11.25). The
source can be found [here](https://github.com/astral-sh/uv/blob/0.11.25/crates/uv-platform).

See uv's
[crate versioning policy](https://docs.astral.sh/uv/reference/policies/versioning/#crate-versioning)
for details on versioning.
```

### File: `crates/uv-scripts/README.md`

```
<!-- This file is generated. DO NOT EDIT -->

# uv-scripts

This crate is an internal component of [uv](https://crates.io/crates/uv). The Rust API exposed here
is unstable and will have frequent breaking changes.

This version (0.0.58) is a component of [uv 0.11.25](https://crates.io/crates/uv/0.11.25). The
source can be found [here](https://github.com/astral-sh/uv/blob/0.11.25/crates/uv-scripts).

See uv's
[crate versioning policy](https://docs.astral.sh/uv/reference/policies/versioning/#crate-versioning)
for details on versioning.
```

### File: `crates/uv-distribution/README.md`

```
<!-- This file is generated. DO NOT EDIT -->

# uv-distribution

This crate is an internal component of [uv](https://crates.io/crates/uv). The Rust API exposed here
is unstable and will have frequent breaking changes.

This version (0.0.58) is a component of [uv 0.11.25](https://crates.io/crates/uv/0.11.25). The
source can be found [here](https://github.com/astral-sh/uv/blob/0.11.25/crates/uv-distribution).

See uv's
[crate versioning policy](https://docs.astral.sh/uv/reference/policies/versioning/#crate-versioning)
for details on versioning.
```

### File: `crates/uv-distribution/src/index/built_wheel_index.rs`

```rust
use std::borrow::Cow;

use uv_cache::{Cache, CacheBucket, CacheShard, WheelCache};
use uv_cache_info::CacheInfo;
use uv_distribution_types::{
    BuildInfo, BuildVariables, ConfigSettings, DirectUrlSourceDist, DirectorySourceDist,
    ExtraBuildRequirement, ExtraBuildRequires, ExtraBuildVariables, GitDirectorySourceDist,
    GitPathSourceDist, Hashed, PackageConfigSettings, PathSourceDist,
};
use uv_normalize::PackageName;
use uv_platform_tags::Tags;
use uv_pypi_types::HashDigests;
use uv_types::HashStrategy;

use crate::Error;
use crate::index::cached_wheel::{CachedWheel, ResolvedWheel};
use crate::source::{
    HASHES, HTTP_REVISION, HttpRevisionPointer, LOCAL_REVISION, LocalRevisionPointer,
    RevisionHashes,
};

/// A local index of built distributions for a specific source distribution.
#[derive(Debug)]
pub struct BuiltWheelIndex<'a> {
    cache: &'a Cache,
    tags: &'a Tags,
    hasher: &'a HashStrategy,
    config_settings: &'a ConfigSettings,
    config_settings_package: &'a PackageConfigSettings,
    extra_build_requires: &'a ExtraBuildRequires,
    extra_build_variables: &'a ExtraBuildVariables,
}

impl<'a> BuiltWheelIndex<'a> {
    /// Initialize an index of built distributions.
    pub fn new(
        cache: &'a Cache,
        tags: &'a Tags,
        hasher: &'a HashStrategy,
        config_settings: &'a ConfigSettings,
        config_settings_package: &'a PackageConfigSettings,
        extra_build_requires: &'a ExtraBuildRequires,
        extra_build_variables: &'a ExtraBuildVariables,
    ) -> Self {
        Self {
            cache,
            tags,
            hasher,
            config_settings,
            config_settings_package,
            extra_build_requires,
            extra_build_variables,
        }
    }

    /// Return the most compatible [`CachedWheel`] for a given source distribution at a direct URL.
    ///
    /// This method does not perform any freshness checks and assumes that the source distribution
    /// is already up-to-date.
    pub fn url(&self, source_dist: &DirectUrlSourceDist) -> Result<Option<CachedWheel>, Error> {
        // For direct URLs, cache directly under the hash of the URL itself.
        let cache_shard = self.cache.shard(
            CacheBucket::SourceDistributions,
            WheelCache::Url(source_dist.url.raw()).root(),
        );

        // Read the revision from the cache.
        let Some(pointer) = HttpRevisionPointer::read_from(cache_shard.entry(HTTP_REVISION))?
        else {
            return Ok(None);
        };

        // Enforce hash-checking by omitting any wheels that don't satisfy the required hashes.
        let revision = pointer.into_revision();
        if !revision.satisfies(self.hasher.get(source_dist)) {
            return Ok(None);
        }

        let cache_shard = cache_shard.shard(revision.id());

        // If there are build settings, we need to scope to a cache shard.
        let config_settings = self.config_settings_for(&source_dist.name);
        let extra_build_deps = self.extra_build_requires_for(&source_dist.name);
        let extra_build_vars = self.extra_build_variables_for(&source_dist.name);
        let build_info =
            BuildInfo::from_settings(&config_settings, extra_build_deps, extra_build_vars);
        let cache_shard = build_info
            .cache_shard()
            .map(|digest| cache_shard.shard(digest))
            .unwrap_or(cache_shard);

        Ok(self.find(&cache_shard).map(|wheel| {
            CachedWheel::from_entry(
                wheel,
                revision.into_hashes(),
                CacheInfo::default(),
                build_info,
            )
        }))
    }

    /// Return the most compatible [`CachedWheel`] for a given source distribution at a local path.
    pub fn path(&self, source_dist: &PathSourceDist) -> Result<Option<CachedWheel>, Error> {
        let cache_shard = self.cache.shard(
            CacheBucket::SourceDistributions,
            WheelCache::Path(&source_dist.url).root(),
        );

        // Read the revision from the cache.
        let Some(pointer) = LocalRevisionPointer::read_from(cache_shard.entry(LOCAL_REVISION))?
        else {
            return Ok(None);
        };

        // If the distribution is stale, omit it from the index.
        let cache_info =
            CacheInfo::from_file(&source_dist.install_path).map_err(Error::CacheRead)?;
        if cache_info != *pointer.cache_info() {
            return Ok(None);
        }
... (truncated)
```

