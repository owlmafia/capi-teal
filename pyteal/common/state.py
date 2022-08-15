from pyteal import *

# set global state
def set_gs(key, value): return Seq(
    App.globalPut(Bytes(key), value)
)

# get global state
def get_gs(key): return Seq(
    App.globalGet(Bytes(key))
)

def decrement_gs(key, value): return Seq(
    set_gs(key, Minus(
        get_gs(key),
        value
    ))
)

def increment_gs(key, value): return Seq(
    set_gs(key, Minus(
        get_gs(key),
        value
    ))
)
