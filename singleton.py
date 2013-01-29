import functools

__all__ = ('Singleton',)
#------------------------------------------------------------------------------#
# Singleton                                                                    #
#------------------------------------------------------------------------------#
def Singleton (async):
    """Singleton asynchronous function

    Returns previously returned future if has not been resolved, otherwise
    calls provided asynchronous function and returns created future.
    """
    saved = [None]
    def saved_clean (result, error):
        saved [0] = None

    @functools.wraps (async)
    def async_single (*args, **keys):
        if saved [0] is not None:
            return saved [0]

        awaiter = async (*args, **keys).Await ()
        if not awaiter.IsCompleted ():
            saved [0] = awaiter
            awaiter.OnCompleted (saved_clean)

        return awaiter

    return async_single