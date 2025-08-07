This is an MCP server for OpenAlgo - (logic is copied from https://github.com/marketcalls/openalgo )

It has been repackaged for use as a module without necessity of cloning repos and installing python script.

Requirements:
- Local 3.12 or higher Python 
- uvx installed

How to Install uvx (uv)
-----------------------

- **Universal (Windows, Linux, Mac):**
  ```sh
  pip install uv
  ```
- **Mac (with Homebrew):**
  ```sh
  brew install uv
  ```
- **Prebuilt binaries:**  
  Download from [uv releases](https://github.com/astral-sh/uv/releases) for your platform.

After installation, the `uvx` command will be available in your terminal.

Addition of an entry similar to below on your favorite MCP Client. The below is tested with Cline plugin on VSCode. 

``` 
 "openalgo": {
      "disabled": false,
      "timeout": 60,
      "type": "stdio",
      "command": "uvx",
      "args": [
        "openalgo-mcp@latest",
        "YOUR-OPENALGO-KEY",
        "http://127.0.0.1:5000"
      ]
    }
```