# Doppkit for GRiD

Doppkit is a tool for interacting with the [USACE GRiD service](https://grid.nga.mil). The primary usage is for downloading the exports for a specific AOI by providing an access token and AOI PK.  Doppkit is designed so it can be functional on computers that may not have a reliable network connection.

For convenience, single-file code-signed binaries for Windows are provided on the [releases page](https://github.com/hobuinc/doppkit/releases).

## Installation and Invocation

### CLI

The text UI to show download progress and log-information is created using the rich library.

From source:

```bash
$ pip install doppkit
...
$ doppkit --help
```

From built executable:

```doscon
> doppkit-cli.exe --help
```

### GUI

The doppkit GUI which uses the PySide6 bindings of the Qt framework.

From source:

```bash
$ pip install "doppkit[GUI]"
...
$ doppkit-gui 
```

Using generated binary:

```doscon
> doppkit.exe
```

## Providing the Token

The token needed to access the AOI can be provided by one of several ways.

1. Add the `--token TOKEN` argument to your command line usage
2. Set the environment variable `GRID_ACCESS_TOKEN`

## Example Command Line Usage

```shell
export GRID_ACCESS_TOKEN=KMCb6Nl799EFPproLLJR8bgeqzd4q
doppkit --progress True list --filter "Chicago"
doppkit --log-level DEBUG --progress True sync 80903
```
