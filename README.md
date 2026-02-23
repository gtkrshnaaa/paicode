# Paicode

Paicode is a command-line based agentic AI tool for software development and automation. It interacts with your local filesystem to read, analyze, and modify code based on natural language instructions.

**Note:** Paicode has only been tested on Linux environments. Compatibility with other operating systems is not guaranteed at this time.

## Installation

The quickest way to install Paicode is via system-wide Python installation or using pipex (recommended for isolated CLI tools).

Ensure you have Python 3.10+ installed.

```bash
# Clone the repository
git clone https://github.com/gtkrshnaaa/paicode.git
cd paicode

# The easiest way to install is via the provided makefile:
# This creates a local virtual environment and installs the 'pai' launcher.
make setup
```

After installation, the `pai` command will be available in your terminal.

## Requirements

You must set your Gemini API key before running Paicode. You can easily do this via the CLI:

```bash
pai set
```

You will then be prompted to enter your API key securely.

## Documentation

For comprehensive information on how Paicode works, its architecture, and the full list of available features, please refer to the `docs/` directory:

- [Key Features & Capabilities](docs/features.md)
- [Usage & Commands](docs/usage.md)
- [Internal Architecture](docs/architecture.md)

## Basic Usage

To run a single prompt:
```bash
pai "create a Python script that prints hello world"
```

To enter interactive mode (recommended for continuous development):
```bash
pai auto
```
