from pyteal import *
from common.constants import *

def is_asset_transfer(tx): return Seq(
    Assert(tx.type_enum() == TxnType.AssetTransfer),
)

def is_shares_transfer(tx): return Seq(
    is_asset_transfer(tx),
    Assert(tx.xfer_asset() == App.globalGet(Bytes(GLOBAL_SHARES_ASSET_ID))),
)

def is_shares_transfer_to_this_app(tx): return Seq(
    is_shares_transfer(tx),
    Assert(tx.asset_receiver() == Global.current_application_address()),
)

def is_funds_transfer(tx): return Seq(
    is_asset_transfer(tx),
    Assert(tx.xfer_asset() == App.globalGet(Bytes(GLOBAL_FUNDS_ASSET_ID))),
)

def is_funds_transfer_to_this_app(tx): return Seq(
    is_funds_transfer(tx),
    Assert(tx.asset_receiver() == Global.current_application_address()),
)
