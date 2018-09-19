import tensorflow as tf
import numpy as np


def attention(inputs, attention_size, time_major=False, return_alphas=False):
    """
    Attention mechanism layer which reduces RNN/Bi-RNN outputs with Attention vector.

    The idea was proposed in the article by Z. Yang et al., "Hierarchical Attention Networks
     for Document Classification", 2016: http://www.aclweb.org/anthology/N16-1174.
    Variables notation is also inherited from the article

    Args:
        inputs: The Attention inputs.
            Matches outputs of RNN/Bi-RNN layer (not final state):
                In case of RNN, this must be RNN outputs `Tensor`:
                    If time_major == False (default), this must be a tensor of shape:
                        `[batch_size, max_time, cell.output_size]`.
                    If time_major == True, this must be a tensor of shape:
                        `[max_time, batch_size, cell.output_size]`.
                In case of Bidirectional RNN, this must be a tuple (outputs_fw, outputs_bw) containing the forward and
                the backward RNN outputs `Tensor`.
                    If time_major == False (default),
                        outputs_fw is a `Tensor` shaped:
                        `[batch_size, max_time, cell_fw.output_size]`
                        and outputs_bw is a `Tensor` shaped:
                        `[batch_size, max_time, cell_bw.output_size]`.
                    If time_major == True,
                        outputs_fw is a `Tensor` shaped:
                        `[max_time, batch_size, cell_fw.output_size]`
                        and outputs_bw is a `Tensor` shaped:
                        `[max_time, batch_size, cell_bw.output_size]`.
        attention_size: Linear size of the Attention weights.
        time_major: The shape format of the `inputs` Tensors.
            If true, these `Tensors` must be shaped `[max_time, batch_size, depth]`.
            If false, these `Tensors` must be shaped `[batch_size, max_time, depth]`.
            Using `time_major = True` is a bit more efficient because it avoids
            transposes at the beginning and end of the RNN calculation.  However,
            most TensorFlow data is batch-major, so by default this function
            accepts input and emits output in batch-major form.
        return_alphas: Whether to return attention coefficients variable along with layer's output.
            Used for visualization purpose.
    Returns:
        The Attention output `Tensor`.
        In case of RNN, this will be a `Tensor` shaped:
            `[batch_size, cell.output_size]`.
        In case of Bidirectional RNN, this will be a `Tensor` shaped:
            `[batch_size, cell_fw.output_size + cell_bw.output_size]`.
    """

    if isinstance(inputs, tuple):
        # In case of Bi-RNN, concatenate the forward and the backward RNN outputs.
        inputs = tf.concat(inputs, 2)

    if time_major:
        # (T,B,D) => (B,T,D)
        inputs = tf.array_ops.transpose(inputs, [1, 0, 2])

    hidden_size = inputs.shape[2].value  # D value - hidden size of the RNN layer

    # Trainable parameters
    w_omega = tf.Variable(tf.random_normal([hidden_size, attention_size], stddev=0.1))
    b_omega = tf.Variable(tf.random_normal([attention_size], stddev=0.1))
    u_omega = tf.Variable(tf.random_normal([attention_size], stddev=0.1))

    with tf.name_scope('v'):
        # Applying fully connected layer with non-linear activation to each of the B*T timestamps;
        #  the shape of `v` is (B,T,D)*(D,A)=(B,T,A), where A=attention_size
        v = tf.tanh(tf.tensordot(inputs, w_omega, axes=1) + b_omega)

    # For each of the timestamps its vector of size A from `v` is reduced with `u` vector
    vu = tf.tensordot(v, u_omega, axes=1, name='vu')  # (B,T) shape
    alphas = tf.nn.softmax(vu, name='alphas')  # (B,T) shape

    # Output of (Bi-)RNN is reduced with attention vector; the result has (B,D) shape
    output = tf.reduce_sum(inputs * tf.expand_dims(alphas, -1), 1)

    if not return_alphas:
        return output
    else:
        return output, alphas

def attention_with_no_size(inputs, time_major=False, return_alphas=False):
    if time_major:
        # (T,B,D) => (B,T,D)
        inputs = tf.array_ops.transpose(inputs, [1, 0, 2])

    batch_size = inputs.shape[0].value
    hidden_size = inputs.shape[2].value
    u_omega = tf.Variable(tf.random_normal([hidden_size], stddev=0.1))
    with tf.name_scope('tan_h'):
        v = tf.tanh(inputs)

    vu = tf.tensordot(v, u_omega, axes=1, name='vu')
    alphas = tf.nn.softmax(vu, name='alphas')
    output = tf.reduce_sum(inputs * tf.expand_dims(alphas, -1), 1)

    if not return_alphas:
        return output
    else:
        return output, alphas


def entity_attention(inputs, e1, e2, attention_size):
    attn = tf.layers.dense(inputs, attention_size, activation=tf.nn.relu,
                           kernel_initializer=tf.contrib.layers.xavier_initializer())  # (N, T_q, C)

    e1_idx = tf.concat([tf.expand_dims(tf.range(tf.shape(e1)[0]), axis=-1), tf.expand_dims(e1, axis=-1)], axis=-1)
    e1_h = tf.gather_nd(attn, e1_idx)
    e2_idx = tf.concat([tf.expand_dims(tf.range(tf.shape(e2)[0]), axis=-1), tf.expand_dims(e2, axis=-1)], axis=-1)
    e2_h = tf.gather_nd(attn, e2_idx)

    e1_expand = tf.expand_dims(e1_h, axis=-1)
    e2_expand = tf.expand_dims(e2_h, axis=-1)
    e = tf.concat([e1_expand, e2_expand], axis=-1)

    # For each of the timestamps its vector of size A from `v` is reduced with `u` vector
    ve = tf.matmul(attn, e, name='ve')  # (B,T,2) shape
    alphas = tf.nn.softmax(ve, name='alphas')  # (B,T,2) shape

    # Output of (Bi-)RNN is reduced with attention vector; the result has (B,D) shape
    output = tf.matmul(alphas, tf.transpose(e, [0, 2, 1]))

    # Normalize
    output = layer_norm(output)  # (N, T_q, C)

    return output


def latent_type_attention(inputs, e1, e2, num_type=3, latent_size=100):
    attn = tf.layers.dense(inputs, latent_size, activation=tf.nn.relu,
                           kernel_initializer=tf.contrib.layers.xavier_initializer())  # (N, T_q, C)
    e1_idx = tf.concat([tf.expand_dims(tf.range(tf.shape(e1)[0]), axis=-1), tf.expand_dims(e1, axis=-1)], axis=-1)
    e1_h = tf.gather_nd(attn, e1_idx)
    e2_idx = tf.concat([tf.expand_dims(tf.range(tf.shape(e2)[0]), axis=-1), tf.expand_dims(e2, axis=-1)], axis=-1)
    e2_h = tf.gather_nd(attn, e2_idx)

    latentT = tf.get_variable("latentT", shape=[num_type, latent_size], initializer=tf.contrib.layers.xavier_initializer())

    # For each of the timestamps its vector of size A from `v` is reduced with `u` vector
    e1_sim = tf.matmul(e1_h, tf.transpose(latentT), name='e1_sim')  # (B,3) shape
    e1_alphas = tf.nn.softmax(e1_sim, name='e1_alphas')  # (B,3) shape
    e1_type = tf.matmul(e1_alphas, latentT, name='e1_type')  # (B, latent_size)

    # For each of the timestamps its vector of size A from `v` is reduced with `u` vector
    e2_sim = tf.matmul(e2_h, tf.transpose(latentT), name='e2_sim')  # (B,3) shape
    e2_alphas = tf.nn.softmax(e2_sim, name='e2_alphas')  # (B,3) shape
    e2_type = tf.matmul(e2_alphas, latentT, name='e2_type')  # (B, latent_size)

    # # Normalize
    # output = layer_norm(output)  # (N, T_q, C)

    return e1_type, e2_type


def multihead_attention(queries,
                        keys,
                        num_units,
                        num_heads,
                        dropout_rate=0,
                        is_training=True,
                        causality=False,
                        scope="multihead_attention",
                        reuse=None):
    '''Applies multihead attention.

    Args:
      queries: A 3d tensor with shape of [N, T_q, C_q].
      keys: A 3d tensor with shape of [N, T_k, C_k].
      num_units: A scalar. Attention size.
      dropout_rate: A floating point number.
      is_training: Boolean. Controller of mechanism for dropout.
      causality: Boolean. If true, units that reference the future are masked.
      num_heads: An int. Number of heads.
      scope: Optional scope for `variable_scope`.
      reuse: Boolean, whether to reuse the weights of a previous layer
        by the same name.

    Returns
      A 3d tensor with shape of (N, T_q, C)
    '''
    with tf.variable_scope(scope, reuse=reuse):
        # Linear projections
        Q = tf.layers.dense(queries, num_units, activation=tf.nn.relu,
                            kernel_initializer=tf.contrib.layers.xavier_initializer())  # (N, T_q, C)
        K = tf.layers.dense(keys, num_units, activation=tf.nn.relu,
                            kernel_initializer=tf.contrib.layers.xavier_initializer())  # (N, T_k, C)
        V = tf.layers.dense(keys, num_units, activation=tf.nn.relu,
                            kernel_initializer=tf.contrib.layers.xavier_initializer())  # (N, T_k, C)

        # Split and concat
        Q_ = tf.concat(tf.split(Q, num_heads, axis=2), axis=0)  # (h*N, T_q, C/h)
        K_ = tf.concat(tf.split(K, num_heads, axis=2), axis=0)  # (h*N, T_k, C/h)
        V_ = tf.concat(tf.split(V, num_heads, axis=2), axis=0)  # (h*N, T_k, C/h)

        # Multiplication
        outputs = tf.matmul(Q_, tf.transpose(K_, [0, 2, 1]))  # (h*N, T_q, T_k)

        # Scale
        outputs /= K_.get_shape().as_list()[-1] ** 0.5

        # Key Masking
        key_masks = tf.sign(tf.abs(tf.reduce_sum(keys, axis=-1)))  # (N, T_k)
        key_masks = tf.tile(key_masks, [num_heads, 1])  # (h*N, T_k)
        key_masks = tf.tile(tf.expand_dims(key_masks, 1), [1, tf.shape(queries)[1], 1])  # (h*N, T_q, T_k)

        paddings = tf.ones_like(outputs) * (-2 ** 32 + 1)
        outputs = tf.where(tf.equal(key_masks, 0), paddings, outputs)  # (h*N, T_q, T_k)

        # Causality = Future blinding
        if causality:
            diag_vals = tf.ones_like(outputs[0, :, :])  # (T_q, T_k)
            tril = tf.contrib.linalg.LinearOperatorTriL(diag_vals).to_dense()  # (T_q, T_k)
            masks = tf.tile(tf.expand_dims(tril, 0), [tf.shape(outputs)[0], 1, 1])  # (h*N, T_q, T_k)

            paddings = tf.ones_like(masks) * (-2 ** 32 + 1)
            outputs = tf.where(tf.equal(masks, 0), paddings, outputs)  # (h*N, T_q, T_k)

        # Activation
        outputs = tf.nn.softmax(outputs)  # (h*N, T_q, T_k)

        # Query Masking
        query_masks = tf.sign(tf.abs(tf.reduce_sum(queries, axis=-1)))  # (N, T_q)
        query_masks = tf.tile(query_masks, [num_heads, 1])  # (h*N, T_q)
        query_masks = tf.tile(tf.expand_dims(query_masks, -1), [1, 1, tf.shape(keys)[1]])  # (h*N, T_q, T_k)
        outputs *= query_masks  # broadcasting. (N, T_q, C)

        # Dropouts
        outputs = tf.layers.dropout(outputs, rate=dropout_rate, training=tf.convert_to_tensor(is_training))

        # Weighted sum
        outputs = tf.matmul(outputs, V_)  # ( h*N, T_q, C/h)

        # Restore shape
        outputs = tf.concat(tf.split(outputs, num_heads, axis=0), axis=2)  # (N, T_q, C)

        # Residual connection
        outputs += queries

        # Normalize
        outputs = layer_norm(outputs)  # (N, T_q, C)

    return outputs


def relative_multihead_attention(queries,
                                 keys,
                                 num_units,
                                 num_heads,
                                 clip_k,
                                 seq_len,
                                 dropout_rate=0,
                                 is_training=True,
                                 causality=False,
                                 scope="relative_multihead_attention",
                                 reuse=None):
    '''Applies multihead attention.

    Args:
      queries: A 3d tensor with shape of [N, T_q, C_q].
      keys: A 3d tensor with shape of [N, T_k, C_k].
      num_units: A scalar. Attention size.
      dropout_rate: A floating point number.
      is_training: Boolean. Controller of mechanism for dropout.
      causality: Boolean. If true, units that reference the future are masked.
      num_heads: An int. Number of heads.
      scope: Optional scope for `variable_scope`.
      reuse: Boolean, whether to reuse the weights of a previous layer
        by the same name.

    Returns
      A 3d tensor with shape of (N, T_q, C)
    '''
    with tf.variable_scope(scope, reuse=reuse):
        # Linear projections
        Q = tf.layers.dense(queries, num_units, activation=tf.nn.relu,
                            kernel_initializer=tf.contrib.layers.xavier_initializer())  # (N, T_q, C)
        K = tf.layers.dense(keys, num_units, activation=tf.nn.relu,
                            kernel_initializer=tf.contrib.layers.xavier_initializer())  # (N, T_k, C)
        V = tf.layers.dense(keys, num_units, activation=tf.nn.relu,
                            kernel_initializer=tf.contrib.layers.xavier_initializer())  # (N, T_k, C)

        # Split and concat
        Q_ = tf.concat(tf.split(Q, num_heads, axis=2), axis=0)  # (h*N, T_q, C/h)
        K_ = tf.concat(tf.split(K, num_heads, axis=2), axis=0)  # (h*N, T_k, C/h)
        V_ = tf.concat(tf.split(V, num_heads, axis=2), axis=0)  # (h*N, T_k, C/h)

        def shift(arr, n):
            if n < 0:
                arr[:n] = arr[-n:]
                arr[n:] = 2*clip_k+1
            elif n > 0:
                arr[n:] = arr[:-n]
                arr[:n] = 1
            return arr
        dist = np.full(seq_len, 2 * clip_k + 1)
        dist[0:2 * clip_k] = np.arange(1, 2 * clip_k + 1)
        dist = tf.convert_to_tensor(np.array([shift(dist.copy(), i) for i in range(-clip_k, seq_len-clip_k)]), name="dist")
        dist = dist[:tf.shape(Q_)[1], :tf.shape(Q_)[1]]

        # Relative Position Embedding
        with tf.device('/cpu:0'), tf.variable_scope("relative-pos-embeddings"):
            WK = tf.Variable(tf.random_uniform([2*clip_k+2, num_units//num_heads], -0.25, 0.25), name="WK")
            aK = tf.nn.embedding_lookup(WK, dist)
            WV = tf.Variable(tf.random_uniform([2 * clip_k + 2, num_units // num_heads], -0.25, 0.25), name="WV")
            aV = tf.nn.embedding_lookup(WV, dist)

        # Multiplication
        outputs = tf.matmul(Q_, tf.transpose(K_, [0, 2, 1]))  # (h*N, T_q, T_k)
        # Relative Position Embedding
        aKT = tf.transpose(aK, [0, 2, 1])
        QaK = tf.matmul(tf.transpose(Q_, [1, 0, 2]), aKT)
        QaK_res = tf.transpose(QaK, [1, 0, 2])
        outputs = tf.add(outputs, QaK_res)

        # Scale
        outputs /= K_.get_shape().as_list()[-1] ** 0.5

        # Key Masking
        key_masks = tf.sign(tf.abs(tf.reduce_sum(keys, axis=-1)))  # (N, T_k)
        key_masks = tf.tile(key_masks, [num_heads, 1])  # (h*N, T_k)
        key_masks = tf.tile(tf.expand_dims(key_masks, 1), [1, tf.shape(queries)[1], 1])  # (h*N, T_q, T_k)

        paddings = tf.ones_like(outputs) * (-2 ** 32 + 1)
        outputs = tf.where(tf.equal(key_masks, 0), paddings, outputs)  # (h*N, T_q, T_k)

        # Causality = Future blinding
        if causality:
            diag_vals = tf.ones_like(outputs[0, :, :])  # (T_q, T_k)
            tril = tf.contrib.linalg.LinearOperatorTriL(diag_vals).to_dense()  # (T_q, T_k)
            masks = tf.tile(tf.expand_dims(tril, 0), [tf.shape(outputs)[0], 1, 1])  # (h*N, T_q, T_k)

            paddings = tf.ones_like(masks) * (-2 ** 32 + 1)
            outputs = tf.where(tf.equal(masks, 0), paddings, outputs)  # (h*N, T_q, T_k)

        # Activation
        outputs = tf.nn.softmax(outputs)  # (h*N, T_q, T_k)

        # Query Masking
        query_masks = tf.sign(tf.abs(tf.reduce_sum(queries, axis=-1)))  # (N, T_q)
        query_masks = tf.tile(query_masks, [num_heads, 1])  # (h*N, T_q)
        query_masks = tf.tile(tf.expand_dims(query_masks, -1), [1, 1, tf.shape(keys)[1]])  # (h*N, T_q, T_k)
        outputs *= query_masks  # broadcasting. (N, T_q, C)

        # Dropouts
        outputs = tf.layers.dropout(outputs, rate=dropout_rate, training=tf.convert_to_tensor(is_training))

        # Relative Position Embedding
        outputs_aV = tf.transpose(tf.matmul(tf.transpose(outputs, [1, 0, 2]), aV), [1, 0, 2])
        # Weighted sum
        outputs = tf.matmul(outputs, V_)  # ( h*N, T_q, C/h)
        outputs = tf.add(outputs, outputs_aV)

        # Restore shape
        outputs = tf.concat(tf.split(outputs, num_heads, axis=0), axis=2)  # (N, T_q, C)

        # Residual connection
        outputs += queries

        # Normalize
        outputs = layer_norm(outputs)  # (N, T_q, C)

    return outputs


def feedforward(inputs,
                num_units=[150, 300],
                scope="multihead_attention",
                reuse=None):
    '''Point-wise feed forward net.

    Args:
      inputs: A 3d tensor with shape of [N, T, C].
      num_units: A list of two integers.
      scope: Optional scope for `variable_scope`.
      reuse: Boolean, whether to reuse the weights of a previous layer
        by the same name.

    Returns:
      A 3d tensor with the same shape and dtype as inputs
    '''
    with tf.variable_scope(scope, reuse=reuse):
        # Inner layer
        params = {"inputs": inputs, "filters": num_units[0], "kernel_size": 1,
                  "activation": tf.nn.relu, "use_bias": True}
        outputs = tf.layers.conv1d(**params)

        # Readout layer
        params = {"inputs": outputs, "filters": num_units[1], "kernel_size": 1,
                  "activation": None, "use_bias": True}
        outputs = tf.layers.conv1d(**params)

        # Residual connection
        outputs += inputs

        # Normalize
        outputs = layer_norm(outputs)

    return outputs


def layer_norm(inputs,
               epsilon=1e-8,
               scope="ln",
               reuse=None):
    '''Applies layer normalization.

    Args:
      inputs: A tensor with 2 or more dimensions, where the first dimension has
        `batch_size`.
      epsilon: A floating number. A very small number for preventing ZeroDivision Error.
      scope: Optional scope for `variable_scope`.
      reuse: Boolean, whether to reuse the weights of a previous layer
        by the same name.

    Returns:
      A tensor with the same shape and data dtype as `inputs`.
    '''
    with tf.variable_scope(scope, reuse=reuse):
        inputs_shape = inputs.get_shape()
        params_shape = inputs_shape[-1:]

        mean, variance = tf.nn.moments(inputs, [-1], keep_dims=True)
        beta = tf.Variable(tf.zeros(params_shape))
        gamma = tf.Variable(tf.ones(params_shape))
        normalized = (inputs - mean) / ((variance + epsilon) ** (.5))
        outputs = gamma * normalized + beta

    return outputs
