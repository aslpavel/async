#Asynchronous programming for Python#

C# like Async/Await paradig for asynchronous programming in Python

##Types##
 * `Future`
 > Main type to keep/pass/wait result of asynchronous operation
 > ###Methods###
 > > `Wait () -> None`
 > > `Cancel () -> None`
 > > `Result () -> T`
 > > `Error () -> (ExceptionType, Exception, Traceback)?`
 > > `IsCompleted () -> bool`
 > > `Continue (cont:Func<Future<T>, TResult>) -> Future<TResult>`
 > > `ContinueWithFunction (func:Func<T, TResult>) -> Future<TResult>`
 > > `ContinueWithAsync (async:Func<T, Future<TResult>>) -> Future<TResult>

 * `Core`
 > Asynchronous core for IO/Sleep operations
 > ###Methods###
 > > `Poll (fd:int, mask:int) -> Future<int>`
 > > `Sleep (delay:float) -> Future<float>`
 > > `SleepUntil (time:float) -> Future<float>`

##Decorators##
 * `Async`
 > Decorator converting generator to asynchronous function

 * `DummyAsync`
 > Create

 * `Serialize`
 > Serialize access to asynchronous function

##Example##
>     @Async
>     def ProcessAssync ():
>        try:
>            data = yield GetAsync ()
>        except TimoutError:
>            return
>        AsyncReturn ((yield CompressAsync (data)))
