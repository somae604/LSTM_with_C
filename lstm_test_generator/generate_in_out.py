import onnx
import onnxruntime
from onnx import helper, numpy_helper
from onnx import shape_inference
from onnx import IR_VERSION
import numpy as np

def generate_model(rnn_type, input_dim, hidden_dim, bidirectional, layers, model_name, batch_one=True,
                   has_seq_len=False, s_len=1):
    model = onnx.ModelProto()
    model.ir_version = IR_VERSION

    opset = model.opset_import.add()
    opset.domain == 'onnx'
    opset.version = 11
    num_directions = 2 if bidirectional else 1

    X = 'input'
    model.graph.input.add().CopyFrom(
        helper.make_tensor_value_info(X, onnx.TensorProto.FLOAT, [s_len, 1 if batch_one else 'b', input_dim]))
    model.graph.initializer.add().CopyFrom(numpy_helper.from_array(np.asarray([0, 0, -1], dtype=np.int64), 'shape'))

    if has_seq_len:
        seq_len = 'seq_len'
        model.graph.input.add().CopyFrom(
            helper.make_tensor_value_info(seq_len, onnx.TensorProto.INT32, [1 if batch_one else 'b', ]))

    gates = {'lstm': 4, 'gru': 3, 'rnn': 1}[rnn_type]
    for i in range(layers):
        layer_input_dim = (input_dim if i == 0 else hidden_dim * num_directions)
        model.graph.initializer.add().CopyFrom(numpy_helper.from_array(
            np.random.rand(num_directions, gates * hidden_dim, layer_input_dim).astype(np.float32), 'W' + str(i)))
        model.graph.initializer.add().CopyFrom(
            numpy_helper.from_array(np.random.rand(num_directions, gates * hidden_dim, hidden_dim).astype(np.float32),
                                    'R' + str(i)))
        model.graph.initializer.add().CopyFrom(
            numpy_helper.from_array(np.random.rand(num_directions, 2 * gates * hidden_dim).astype(np.float32),
                                    'B' + str(i)))
        layer_inputs = [X, 'W' + str(i), 'R' + str(i), 'B' + str(i)]
        if has_seq_len:
            layer_inputs += [seq_len]
        layer_outputs = ['layer_output_' + str(i)]
        model.graph.node.add().CopyFrom(
            helper.make_node(rnn_type.upper(), layer_inputs, layer_outputs, rnn_type + str(i), hidden_size=hidden_dim,
                             direction='bidirectional' if bidirectional else 'forward'))
        model.graph.node.add().CopyFrom(
            helper.make_node('Transpose', layer_outputs, ['transposed_output_' + str(i)], 'transpose' + str(i),
                             perm=[0, 2, 1, 3]))
        model.graph.node.add().CopyFrom(
            helper.make_node('Reshape', ['transposed_output_' + str(i), 'shape'], ['reshaped_output_' + str(i)],
                             'reshape' + str(i)))
        X = 'reshaped_output_' + str(i)
    model.graph.output.add().CopyFrom(
        helper.make_tensor_value_info(X, onnx.TensorProto.FLOAT, [s_len, 'b', hidden_dim * num_directions]))
    model = shape_inference.infer_shapes(model)
    onnx.save(model, model_name)

# rnn_type, input_dim, hidden_dim, bidirectional,  layers,   model_name, batch_one=True,  has_seq_len=False, s_len=1
generate_model("lstm", 128, 32, False, 1, "model.onnx", True, False, 1)

input = np.random.rand(1, 1, 128).astype(np.float32)

# Convert the Numpy array to a TensorProto
tensor = numpy_helper.from_array(input)

# Save the TensorProto
with open('test_data_set_0/input_0.pb', 'wb') as f:
    f.write(tensor.SerializeToString())

# with CustomObjectScope({'GlorotUniform': glorot_uniform()}):
sess = onnxruntime.InferenceSession("model.onnx")
result = sess.run(["reshaped_output_0"], {'input': input.astype(np.float32)})
print("ONNX Runtime")
print(np.asarray(result[0]))

# Convert the Numpy array to a TensorProto
tensor = numpy_helper.from_array(np.asarray(result[0]))

# Save the TensorProto
with open('test_data_set_0/output_0.pb', 'wb') as f:
    f.write(tensor.SerializeToString())