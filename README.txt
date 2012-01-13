Asynchronous programming for Python
-----------------------------------
C# like Async/Await paradig for asynchronous programming in Python

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
     @Async
     def ProcessAssync ():
        try:
            data = yield GetAsync ()
        except TimoutError:
            return
        AsyncReturn ((yield CompressAsync (data)))
