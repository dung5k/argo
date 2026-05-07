import torch
cp = torch.load('workspaces/CFG_LTC_ASIAN_V3_5/runs/run_20260504_192200_v4_hour_lookback/brains/aamt_v3_CFG_LTC_ASIAN_V3_5_final.pth', map_location='cpu')
print("Keys:", cp.keys())
if 'model_state_dict' in cp:
    # Look at input layer weight to get input_dim
    weight = cp['model_state_dict']['encoder.input_projection.weight']
    print("Input dim from weight:", weight.shape[1])
