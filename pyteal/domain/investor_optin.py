from pyteal import *
from common.constants import *

def investor_optin_init_state(): return Seq(
    # initialize local state with default values
    # why: for general sanity, our app checks always for expected local state length
    # if investor interrups the investing flow after opting in, local state length will be 0
    # and the app will throw an error when reading it
    # we might remove these checks later, in which case this initialization can be removed
    # we'll keep them for now, at least until ready for a security audit
    App.localPut(Gtxn[0].sender(), Bytes(LOCAL_SHARES), Int(0)),
    App.localPut(Gtxn[0].sender(), Bytes(LOCAL_CLAIMED_TOTAL), Int(0)),
    App.localPut(Gtxn[0].sender(), Bytes(LOCAL_CLAIMED_INIT), Int(0)),
    App.localPut(Gtxn[0].sender(), Bytes(LOCAL_SIGNED_PROSPECTUS_URL), Bytes("")),
    App.localPut(Gtxn[0].sender(), Bytes(LOCAL_SIGNED_PROSPECTUS_HASH), Bytes("")),
    App.localPut(Gtxn[0].sender(), Bytes(LOCAL_SIGNED_PROSPECTUS_TIMESTAMP), Bytes("")),
)
