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
        Assert(Gtxn[3].asset_receiver() == Gtxn[3].sender()),

        Approve()
    )

    # TODO are the 2x checks with the app meaningful, maybe if the app has bugs
    handle_drain = Seq(
        Assert(Global.group_size() == Int(3)),

        # call app to verify amount and update state
        Assert(Gtxn[0].type_enum() == TxnType.ApplicationCall),
        Assert(Gtxn[0].on_completion() == OnComplete.NoOp),
        Assert(Gtxn[0].application_id() == tmpl_central_app_id),

        # drain: funds xfer to app escrow
        Assert(Gtxn[1].type_enum() == TxnType.AssetTransfer),
        Assert(Gtxn[1].asset_amount() > Int(0)),
        # the funds are being drained to the app escrow
        Assert(Gtxn[1].asset_receiver() == tmpl_app_escrow_address),
        Assert(Gtxn[1].fee() == Int(0)),
        Assert(Gtxn[1].asset_close_to() == Global.zero_address()),
        Assert(Gtxn[1].rekey_to() == Global.zero_address()),
        # both xfers are signed by the customer escrow
        Assert(Gtxn[1].sender() == Gtxn[2].sender()),

        # pay capi fee: funds xfer to capi escrow
        Assert(Gtxn[2].type_enum() == TxnType.AssetTransfer),
        # the capi fee is being sent to the capi escrow
        Assert(Gtxn[2].asset_receiver() == tmpl_capi_escrow_address),
        Assert(Gtxn[2].fee() == Int(0)),
        Assert(Gtxn[2].asset_close_to() == Global.zero_address()),
        Assert(Gtxn[2].rekey_to() == Global.zero_address()),

        Approve()
    )

    program = Cond(
        [Global.group_size() == Int(5), handle_setup_dao],
        [Gtxn[0].application_args[0] == Bytes("drain"), handle_drain],
    )

    program = Approve()

    return compileTeal(program, Mode.Signature, version=6)


path = 'teal_template/customer_escrow.teal'
with open(path, 'w') as f:
    output = program()
    # print(output)
    f.write(output)
    print("Done! Wrote customer escrow TEAL to: " + path)
