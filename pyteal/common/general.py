from pyteal import *
from common.constants import *

def is_group_size(size): return Seq(
    Assert(Global.group_size() == Int(size)),
)

def is_args_length(tx, length): return Seq(
    Assert(is_args_length_res(tx, length)), 
)

def is_args_length_res(tx, length): return Seq(
    tx.application_args.length() == Int(length), 
)
