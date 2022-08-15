from pyteal import *
from functions.constants import *

def is_payment_to_this_app(tx): return Seq(
    Assert(tx.type_enum() == TxnType.Payment),
    Assert(tx.receiver() == Global.current_application_address()),
)