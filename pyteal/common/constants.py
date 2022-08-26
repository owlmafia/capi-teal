from pyteal import *

tmpl_share_price = Tmpl.Int("TMPL_SHARE_PRICE")
tmpl_capi_escrow_address = Tmpl.Addr("TMPL_CAPI_ESCROW_ADDRESS")
# note "__" at the end so text isn't contained in TMPL_PRECISION_SQUARE
tmpl_precision = Tmpl.Int("TMPL_PRECISION__")
tmpl_capi_share = Tmpl.Int("TMPL_CAPI_SHARE")
tmpl_precision_square = Tmpl.Int("TMPL_PRECISION_SQUARE")
tmpl_investors_share = Tmpl.Int("TMPL_INVESTORS_SHARE")
tmpl_share_supply = Tmpl.Int("TMPL_SHARE_SUPPLY")
tmpl_max_raisable_amount = Tmpl.Int("TMPL_MAX_RAISABLE_AMOUNT")

GLOBAL_RECEIVED_TOTAL = "CentralReceivedTotal"
GLOBAL_AVAILABLE_AMOUNT = "AvailableAmount"

GLOBAL_SHARES_ASSET_ID = "SharesAssetId"
GLOBAL_FUNDS_ASSET_ID = "FundsAssetId"

GLOBAL_LOCKED_SHARES = "LockedShares"

GLOBAL_DAO_NAME = "DaoName"
GLOBAL_DAO_DESC = "DaoDesc"
GLOBAL_SHARE_PRICE = "SharePrice"
# % of income directed to investors
GLOBAL_INVESTORS_PART = "InvestorsPart"

GLOBAL_SOCIAL_MEDIA_URL = "SocialMediaUrl"
GLOBAL_HOMEPAGE = "HomepageUrl"

GLOBAL_TARGET = "Target"
# Date where the dao was setup
# it's likely possible to get this via indexer, instead of storing it in teal
# but for now this seems fine - it's just 4 more lines in TEAL, less requests when loading a dao, and quicker to implement.
GLOBAL_SETUP_DATE = "SetupDate"
GLOBAL_TARGET_END_DATE = "TargetEndDate"
GLOBAL_RAISED = "Raised"

GLOBAL_IMAGE_ASSET_ID = "ImageAsset"
GLOBAL_IMAGE_URL = "ImageUrl"
# can be an empty string (equivalent to "none")
# note that this is handled different than the image url - for the later,
# we make it actually optional, to more easily detect here that it's not set and not create the NFT.
GLOBAL_PROSPECTUS_URL = "ProspectusUrl"
GLOBAL_PROSPECTUS_HASH = "ProspectusHash"

GLOBAL_VERSIONS = "Versions"

GLOBAL_MIN_INVEST_AMOUNT = "GlobalMinInvestAmount"
GLOBAL_MAX_INVEST_AMOUNT = "GlobalMaxInvestAmount"

LOCAL_SHARES = "Shares"
LOCAL_CLAIMED_TOTAL = "ClaimedTotal"
LOCAL_CLAIMED_INIT = "ClaimedInit"

# Prospectus acknowledged by investor, when investing
# Note: investor can store (by means other than our app) an inconsistent url-hash (teal can't prove this)
# but they're not incentivized to do this: anyone can prove that the combination is invalid
# as the url contains an IPFS CID which is also a hash of the document
# (if the document that corresponds to the url/CID can't be hashed to our hash, it's invalid)
# Note: we need a hash additionally to the CID, because the CID algorithm is IPFS specific and it's unclear how it works exactly
LOCAL_SIGNED_PROSPECTUS_URL= "SignedProspectusUrl"
LOCAL_SIGNED_PROSPECTUS_HASH= "SignedProspectusHash"
LOCAL_SIGNED_PROSPECTUS_TIMESTAMP= "SignedProspectusTimestamp"
