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
    set_gs(key, Add(
        get_gs(key),
        value
    ))
)

# set local state
def set_ls(owner, key, value): return Seq(
    App.localPut(owner, Bytes(key), value),
)

def get_ls(owner, key): return Seq(
    App.localGet(owner, Bytes(key)),
)

def increment_ls(owner, key, value): return Seq(
    set_ls(owner, key, Add(
        get_ls(owner, key),
        value
    )),
)

def decrement_ls(owner, key, value): return Seq(
    set_ls(owner, key, Minus(
        get_ls(owner, key),
        value
    )),
)