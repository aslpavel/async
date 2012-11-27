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
    future_saved = [None]
    def future_resolve (result, error):
        future_saved [0] = None

    def async_single (*args, **keys):
        if future_saved [0] is not None:
            return future_saved [0]

        future = async (*args, **keys)
        future_saved [0] = future
        future.Continue (future_resolve)
        return future

    return functools.update_wrapper (async_single, async)