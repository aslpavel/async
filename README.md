# Asynchronous framework (Depricated use "pretzel.monad" instead)

C# like Async/Await paradigm for asynchronous programming in Python

## Example:

```python
import socket
from async import Async, BufferedSocket, Core, BrokenPipeError

def main ():
    @Async
    def server (port, addr = None):
        try:
            with BufferedSocket (socket.socket ()) as sock:
                sock.Bind   ((addr or 'localhost', port))
                sock.Listen (10)
                while True:
                    echo (*(yield sock.Accept ())).Traceback ('process')
        finally:
            core.Dispose ()

    @Async
    def echo (sock, addr):
        try:
            while True:
                yield sock.Write ((yield sock.Read (1 << 20)))
                yield sock.Flush ()

        except BrokenPipeError: pass
        finally:
            sock.Dispose ()


    with Core.Instance () as core:
        server (port = 8000).Traceback ('server')
        if not core.Disposed:
            core ()

if __name__ == '__main__':
    main ()
```
