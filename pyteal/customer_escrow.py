from pyteal import *

"""Customer escrow"""

tmpl_central_app_id = Tmpl.Int("TMPL_CENTRAL_APP_ID")
tmpl_app_escrow_address = Tmpl.Addr("TMPL_APP_ESCROW_ADDRESS")
tmpl_capi_escrow_address = Tmpl.Addr("TMPL_CAPI_ESCROW_ADDRESS")

GLOBAL_RECEIVED_TOTAL = "ReceivedTotal"
LOCAL_CLAIMED_TOTAL = "ClaimedTotal"
LOCAL_SHARES = "Shares"

def program():
    handle_setup_dao = Seq(
        # app call
        Assert(Gtxn[1].type_enum() == TxnType.ApplicationCall),
        Assert(Gtxn[1].application_id() == tmpl_central_app_id),
        Assert(Gtxn[1].on_completion() == OnComplete.NoOp),

        # customer escrow opt-ins to funds asset
        Assert(Gtxn[3].type_enum() == TxnType.AssetTransfer),
        Assert(Gtxn[3].asset_amount() == Int(0)),

        Approve()
    )

    handle_drain = Seq(
        Assert(Global.group_size() == Int(4)),

        # call app to verify amount and update state
        Assert(Gtxn[0].type_enum() == TxnType.ApplicationCall),
        Assert(Gtxn[0].on_completion() == OnComplete.NoOp),
        Assert(Gtxn[0].sender() == Gtxn[1].sender()), # same user is calling both apps

        # call capi app to update state
        Assert(Gtxn[1].type_enum() == TxnType.ApplicationCall),
        Assert(Gtxn[1].on_completion() == OnComplete.NoOp),

        # drain: funds xfer to app escrow
        Assert(Gtxn[2].type_enum() == TxnType.AssetTransfer),
        Assert(Gtxn[2].asset_amount() > Int(0)),
        Assert(Gtxn[2].asset_receiver() == tmpl_app_escrow_address), # the funds are being drained to the app escrow
        Assert(Gtxn[2].fee() == Int(0)),
        Assert(Gtxn[2].asset_close_to() == Global.zero_address()),
        Assert(Gtxn[2].rekey_to() == Global.zero_address()),

        # pay capi fee: funds xfer to capi escrow
        Assert(Gtxn[3].type_enum() == TxnType.AssetTransfer),
        Assert(Gtxn[3].asset_receiver() == tmpl_capi_escrow_address), # the capi fee is being sent to the capi escrow
        Assert(Gtxn[3].fee() == Int(0)),
        Assert(Gtxn[3].asset_close_to() == Global.zero_address()),
        Assert(Gtxn[3].rekey_to() == Global.zero_address()),

        Approve()
    )

    program = Cond(
        [Global.group_size() == Int(5), handle_setup_dao],
        [Gtxn[0].application_args[0] == Bytes("drain"), handle_drain],
    )

    return compileTeal(program, Mode.Signature, version=6)

path = 'teal_template/customer_escrow.teal'
with open(path, 'w') as f:
    output = program()
    # print(output)
    f.write(output)
    print("Done! Wrote customer escrow TEAL to: " + path)

