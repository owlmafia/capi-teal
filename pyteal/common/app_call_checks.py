from pyteal import *

def is_app_call(tx): return Seq(
    Assert(tx.type_enum() == TxnType.ApplicationCall),
)

def is_app_call_by_creator(tx): return Seq(
    is_app_call(tx),
    Assert(tx.sender() == Global.creator_address()),
)

def is_this_app_call(tx): return Seq(
    is_app_call(tx),
    Assert(tx.application_id() == Global.current_application_id()),
)

def is_this_noop_app_call(tx): return Seq(
    is_this_app_call(tx),
    Assert(tx.on_completion() == OnComplete.NoOp),
)

def is_app_call_this_app_by_creator(tx): return Seq(
    is_app_call_by_creator(tx),
    Assert(tx.application_id() == Global.current_application_id()),
)

def is_app_call_noop_this_app_by_creator(tx): return Seq(
    is_app_call_this_app_by_creator(tx),
    Assert(tx.on_completion() == OnComplete.NoOp),
)
