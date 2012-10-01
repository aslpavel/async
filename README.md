# Asynchronous framework

C# like Async/Await paradigm for asynchronous programming in Python

## Example:

```python
import socket
from async import Async, AsyncSocket, Core

def main ():
    with Core.Instance () as core:
        sock = AsyncSocket (socket.socket ())
        sock.Bind   (('localhost', 8000))
        sock.Listen (10)

        @Async
        def process (sock, addr):
            while True:
                yield sock.Write ((yield sock.Read (1 << 20)))

        @Async
        def server ():
            while True:
                process (*(yield sock.Accept ())).Traceback ('process')

        server ().Traceback ('server')
        core.Execute ()

if __name__ == '__main__':
    main ()
```