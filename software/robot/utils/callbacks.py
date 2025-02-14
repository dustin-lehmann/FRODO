import enum


class Callback:
    parameters: dict
    lambdas: dict
    function: callable

    def __init__(self, function: callable, parameters: dict = None, lambdas: dict = None, discard_inputs: bool = False):
        self.function = function


        if parameters is None:
            parameters = {}
        self.parameters = parameters

        if lambdas is None:
            lambdas = {}
        self.lambdas = lambdas

        self.discard_inputs = discard_inputs

    def __call__(self, *args, **kwargs):
        lambdas_exec = {key: value() for (key, value) in self.lambdas.items()}

        if self.discard_inputs:
            ret = self.function(**{**self.parameters, **lambdas_exec})
        else:
            ret = self.function(*args, **{**self.parameters, **kwargs, **lambdas_exec})

        return ret


class CallbackContainer:
    callbacks: list[Callback]

    def __init__(self):
        self.callbacks = []

    def register(self,  function, parameters: dict = None, lambdas: dict = None, discard_inputs = False):
        callback = Callback(function, parameters, lambdas, discard_inputs)
        self.callbacks.append(callback)

    def remove(self, callback):
        if isinstance(callback, Callback):
            self.callbacks.remove(callback)
        elif callable(callback):
            cb = next(cb for cb in self.callbacks if cb.function == callback)
            self.callbacks.remove(cb)

    def call(self, *args, **kwargs):
        for callback in self.callbacks:
            callback(*args, **kwargs)

    def __iter__(self):
        # Return an iterator over the callbacks list
        return iter(self.callbacks)


def callback_handler(cls):
    original_init = cls.__init__

    def new_init(self, *args, **kwargs):
        for name, annotation in cls.__annotations__.items():
            if annotation is CallbackContainer:
                setattr(self, name, CallbackContainer())
        if original_init:
            original_init(self, *args, **kwargs)

    cls.__init__ = new_init
    return cls



# class CallbackHandler:
#
#     def __init__(self, callbacks):
#
#         self.callbacks = {}
#
#         for member in callbacks:
#             if hasattr(member, 'name'):
#                 self.callbacks[member.name] = []
#             elif isinstance(member, str):
#                 self.callbacks[member] = []
#
#     def call(self, callback_id, *args, **kwargs):
#         for callback in self.callbacks[callback_id]:
#             callback(*args, **kwargs)
#
#     def register(self, callback_id, function, parameters: dict = None, lambdas: dict = None, discard_inputs = False):
#         callback = Callback(function, parameters, lambdas, discard_inputs)
#
#         if isinstance(callback_id, enum.Enum):
#             callback_id = callback_id.name
#
#         if callback_id in self.callbacks:
#             self.callbacks[callback_id].append(callback)
#         else:
#             raise Exception("Invalid Callback type")
#
#     def __getitem__(self, callback_id):
#         """
#         Allow accessing the list of callbacks using bracket notation.
#         """
#         if isinstance(callback_id, enum.Enum):
#             callback_id = callback_id.name
#
#         if callback_id in self.callbacks:
#             return self.callbacks[callback_id]
#         else:
#             raise KeyError(f"Callback ID '{callback_id}' not found.")
#
#
# def callbackdef(cls):
#     """
#     A decorator to automatically assign `enum.auto()` to all members of the Enum.
#     """
#     for name in cls.__annotations__:
#         setattr(cls, name, enum.auto())
#     return enum.Enum(cls.__name__, {k: v for k, v in cls.__dict__.items() if not k.startswith('_')})
