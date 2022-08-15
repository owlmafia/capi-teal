from pyteal import *
from common.constants import *

def save_prospectus(sender, args, first_arg_index): return Seq(
    App.localPut(sender, Bytes(LOCAL_SIGNED_PROSPECTUS_URL), args[first_arg_index]),
    App.localPut(sender, Bytes(LOCAL_SIGNED_PROSPECTUS_HASH), args[first_arg_index + 1]),
    App.localPut(sender, Bytes(LOCAL_SIGNED_PROSPECTUS_TIMESTAMP), args[first_arg_index + 2]),
)
