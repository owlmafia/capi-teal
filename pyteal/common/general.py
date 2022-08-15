from pyteal import *
from common.constants import *

def is_group_size(size): return Seq(
    Assert(Global.group_size() == Int(size)),
)
