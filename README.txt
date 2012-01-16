Asynchronous programming for Python
-----------------------------------
C# like Async/Await paradigm for asynchronous programming in Python

Types:
------
    Future:
        Main type to keep/pass/wait result of asynchronous operation

        Methods:
            Result () -> T
                Get result of future
                if future is completed successfuly returns result of the future
                if future is faield reraise the error
                if future is not completed reise FutureNotReady

            Wait () -> None
                Wait for future to complete

            Cancel () -> None
                Cancel future

            Error () -> (ExceptionType, Exception, Traceback)?
                Error or None if future is completed successfuly or not completed

            IsCompleted () -> bool
                Check if future is completed

            Continue (cont:Func<Future<T>, TResult>) -> Future<TResult>
                Continue with function "cont" with future as argument

            ContinueWithFunction (func:Func<T, TResult>) -> Future<TResult>
                Continue with function "func" with result as argument

            ContinueWithAsync (async:Func<T, Future<TResult>>) -> Future<TResult>
                Continue with asynchronous function "async" and pass result as argume

    Core:
        Asynchronous core for IO/Sleep operations

        Methods:
            Poll (fd:int, mask:int) -> Future<int>
                Wait for "mask" event on descriptor "fd" on success return event mask
                It also can raise:
                    CoreHUPError  - the device has been disconnected
                    CoreNVALError - the specified fd is invalid
                    CoreIOError   - an error has occurred on the device or stream

            Sleep (delay:float) -> Future<float>
                Complete future after at least "delay" seconds have passed

            SleepUntil (time:float) -> Future<float>
                Compolete future after "time" (unix time) has been reached

            AsyncSocketCreate (sock:socket.socket) -> AsyncSocket
                AsyncSocket is a socket with additional asynchronous methods
                    Accept - accept connection
                    Recv   - recv data
                    Send   - send data

Decorators:
-----------
    Async:
        Decorator converting generator to asynchronous function

    DummyAsync:
        Wrap result of funciton into Future

    Serialize:
        Serialize access to asynchronous function

Examples:
--------
    Echo server example:
        import socket
        import traceback
        from async import *

        # print exception continuation function
        def print_exc (future):
            try: return future.Result ()
            except Exception:
                traceback.print_exc ()
                raise

        def main ():
            # create core
            with Core () as core:
                # create server socket
                sock = core.AsyncSocketCreate (socket.socket ())
                sock.bind (('localhost', 8000))
                sock.listen (10)

                @Async
                def handle (client):
                    while True:
                        # wait for new data
                        data = yield client.Recv (1 << 20)

                        if len (data) == 0:
                            # connection has been closed
                            return

                        # wait for data to be send
                        yield client.Send (data)

                @Async
                def accept ():
                    while True:
                        # wait for new connection
                        client, addr = yield sock.Accept ()

                        # create coroutine for handling this client
                        handle (client).Continue (print_exc)

                # start accepting coroutine
                accept ().Continue (print_exc)

        if __name__ == '__main__':
            main ()
