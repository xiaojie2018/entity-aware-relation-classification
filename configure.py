import argparse
import sys


def parse_args():
    """
    Parse input arguments
    """
    parser = argparse.ArgumentParser()

    # Data loading params
    parser.add_argument("--train_path", default="SemEval2010_task8_all_data/SemEval2010_task8_training/TRAIN_FILE.TXT",
                        type=str, help="Path of train data")
    parser.add_argument("--test_path", default="SemEval2010_task8_all_data/SemEval2010_task8_testing_keys/TEST_FILE_FULL.TXT",
                        type=str, help="Path of test data")
    parser.add_argument("--dev_sample_percentage", default=0.1,
                        type=float, help="Percentage of the training data to use for validation")
    parser.add_argument("--max_sentence_length", default=102,
                        type=int, help="Max sentence length in data")
    parser.add_argument("--vocab_path", default=None,
                        type=str, help="Path of vocabulary")

    # Model Hyper-parameters
    parser.add_argument("--word2vec", default=None,
                        type=str, help="Word2vec file with pre-trained embeddings")
    parser.add_argument("--elmo", default=True,
                        type=bool, help="ELMo embeddings")
    parser.add_argument("--embedding_size", default=300,
                        type=int, help="Dimensionality of character embedding (default: 300)")
    # parser.add_argument("--dist_embedding_dim", default=50,
    #                     type=int, help="Dimensionality of character embedding (default: 50)")
    parser.add_argument("--hidden_size", default=512,
                        type=int, help="Dimensionality of RNN hidden (default: 512)")
    parser.add_argument("--attention_size", default=50,
                        type=int, help="Dimensionality of attention (default: 50)")
    parser.add_argument("--rnn_dropout_keep_prob", default=0.8,
                        type=float, help="Dropout keep probability of RNN (default: 0.8)")
    parser.add_argument("--dropout_keep_prob", default=0.5,
                        type=float, help="Dropout keep probability of output layer (default: 0.5)")
    parser.add_argument("--l2_reg_lambda", default=0.0,
                        type=float, help="L2 regularization lambda (default: 0.0)")

    # Training parameters
    parser.add_argument("--batch_size", default=64,
                        type=int, help="Batch Size (default: 64)")
    parser.add_argument("--num_epochs", default=100,
                        type=int, help="Number of training epochs (Default: 100)")
    parser.add_argument("--display_every", default=10,
                        type=int, help="Number of iterations to display training information")
    parser.add_argument("--evaluate_every", default=100,
                        type=int, help="Evaluate model on dev set after this many steps (default: 100)")
    parser.add_argument("--num_checkpoints", default=10,
                        type=int, help="Number of checkpoints to store (default: 5)")
    parser.add_argument("--learning_rate", default=1e-4,
                        type=float, help="Which learning rate to start with (Default: 1e-4)")

    # Testing Parameters
    parser.add_argument("--checkpoint_dir", default="",
                        type=str, help="Checkpoint directory from training run")
    parser.add_argument("--output_path", default="result/output.txt",
                        type=str, help="Path of prediction for evaluation data")
    parser.add_argument("--target_path", default="result/target.txt",
                        type=str, help="Path of target(answer) file for evaluation data")

    # Misc Parameters
    parser.add_argument("--allow_soft_placement", default=True,
                        type=bool, help="Allow device soft device placement")
    parser.add_argument("--log_device_placement", default=False,
                        type=bool, help="Log placement of ops on devices")

    if len(sys.argv) == 0:
        parser.print_help()
        sys.exit(1)

    args = parser.parse_args()
    return args
