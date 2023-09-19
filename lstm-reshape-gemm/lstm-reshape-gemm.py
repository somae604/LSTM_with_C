import onnx
import onnxruntime
from onnx import helper, numpy_helper
from onnx import shape_inference
import numpy as np

# LSTM's input and weight definition
X = helper.make_tensor_value_info('X', onnx.TensorProto.FLOAT, [10, 1, 1])
W_shape = [1, 4*128, 1]
R_shape = [1, 4*128, 128]
B_shape = [1, 8*128]
W = numpy_helper.from_array(np.random.randn(*W_shape).astype(np.float32), "W")
R = numpy_helper.from_array(np.random.randn(*R_shape).astype(np.float32), "R")
B = numpy_helper.from_array(np.random.randn(*B_shape).astype(np.float32), "B")

# LSTM node definition
lstm_node = onnx.helper.make_node(
    'LSTM',
    inputs=['X', 'W', 'R', 'B'],
    outputs=['Y', 'Y_h', 'Y_c'],
    hidden_size=128,
    #activations=['sigmoid', 'tanh', 'tanh'],
    direction='forward',
    input_forget=0
)

# Reshape the sliced output to be [1, 20]
shape_tensor = numpy_helper.from_array(np.array([1, 128], dtype=np.int64), "shape_tensor")
reshape_node = helper.make_node(
    'Reshape',
    inputs=['Y_h', 'shape_tensor'],
    outputs=['reshaped_last_hidden']
)

# Fully Connected (Dense) layer weights and bias definition
dense_weight = numpy_helper.from_array(np.random.randn(1, 128).astype(np.float32), "dense_weight")
dense_bias = numpy_helper.from_array(np.random.randn(1).astype(np.float32), "dense_bias")

# Gemm (Fully Connected) node definition
gemm_node = helper.make_node(
    'Gemm',
    inputs=['reshaped_last_hidden', 'dense_weight', 'dense_bias'],
    outputs=['dense_out'],
    transB=1
)



# Construct the graph
graph = helper.make_graph(
    [lstm_node, reshape_node, gemm_node],
    "LSTM_Reshape_Gemm_Example",
    [X],
    [helper.make_tensor_value_info('dense_out', onnx.TensorProto.FLOAT, [1, 1])],
    [W, R, B, shape_tensor, dense_weight, dense_bias]
)

# Create the model
model = helper.make_model(graph, producer_name='onnx-lstm-reshape-gemm')

# Add shape inference
inferred_model = shape_inference.infer_shapes(model)

# Save the ONNX model
onnx.save(inferred_model, "lstm-reshape-gemm.onnx")

# Load the model and validate by running inference
ort_session = onnxruntime.InferenceSession("lstm-reshape-gemm.onnx")

# Run inference using some random input data
x_data = np.random.rand(10, 1, 1).astype(np.float32)
ort_inputs = {ort_session.get_inputs()[0].name: x_data}
ort_outs = ort_session.run(None, ort_inputs)
print(ort_outs)
