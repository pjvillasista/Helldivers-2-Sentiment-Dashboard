import pandas as pd
import re
import unicodedata
from nltk.tokenize import RegexpTokenizer
from nltk.corpus import stopwords
import nltk
from emot.emo_unicode import UNICODE_EMOJI
from bertopic import BERTopic
from cuml.cluster import HDBSCAN
from sentence_transformers import SentenceTransformer
import logging

# Initialize logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

# Download necessary NLTK resources
nltk.download('stopwords', quiet=True)

def preprocess(text):
    """
    Processes the input text by normalizing, removing noise, and extracting meaningful tokens.

    Args:
        text (str): The text to be processed.

    Returns:
        str: The processed text.
    """
    try:
        # Normalize unicode characters
        text = unicodedata.normalize('NFKD', text).encode('ascii', 'ignore').decode('utf-8', 'ignore')

        # Translate emojis to text
        text = ''.join('_'.join(UNICODE_EMOJI.get(c, c).replace(":", "").replace(",", "").split()) if c in UNICODE_EMOJI else c for c in text)

        # Remove HTML tags and links
        text = re.sub(r'<.*?>|http\S+|www\S+|bit.ly/\S+', '', text)

        # Convert to lowercase and remove selected punctuation
        text = text.lower()
        text = re.sub(r'[.,!?;]', ' ', text)

        # Tokenize and remove stopwords
        token = RegexpTokenizer(r'\w+')
        words = token.tokenize(text)
        cached_stop_words = set(stopwords.words("english")) - {'no', 'not'}
        words = [word for word in words if word not in cached_stop_words]

        return ' '.join(words)

    except Exception as e:
        logging.error(f"Error in text preprocessing: {e}")
        return ""

def setup_topic_model():
    """
    Configures the HDBSCAN and BERTopic models.

    Returns:
        BERTopic: The configured BERTopic model.
    """
    hdbscan_model = HDBSCAN(min_samples=15, min_cluster_size=100, gen_min_span_tree=True, prediction_data=True)
    bertopic_model = BERTopic(language="english", calculate_probabilities=True, verbose=True,
                              embedding_model=SentenceTransformer('all-mpnet-base-v2'), hdbscan_model=hdbscan_model)
    return bertopic_model

def enrich_data_with_topics(data, bertopic_model):
    """
    Enriches data with topics identified by the BERTopic model.

    Args:
        data (DataFrame): The dataframe containing the texts.
        bertopic_model (BERTopic): The pre-configured BERTopic model.

    Returns:
        DataFrame: The enriched DataFrame.
    """
    try:
        topics, probabilities = bertopic_model.fit_transform(data['cleaned_text'])
        data['topic'] = topics
        return data
    except Exception as e:
        logging.error(f"Error in topic modeling: {e}")
        return data

def main():
    logging.info("Loading and cleaning data...")
    reviews_data = pd.read_csv('hd2_reviews.csv')
    clean_data = reviews_data.dropna(subset=['review_text'])
    clean_data['cleaned_text'] = clean_data['review_text'].apply(preprocess)
    clean_data['cleaned_text'] = clean_data['cleaned_text'].astype(str)

    logging.info("Setting up topic modeling...")
    bertopic_model = setup_topic_model()

    logging.info("Enriching data with topics...")
    enriched_data = enrich_data_with_topics(clean_data, bertopic_model)

    logging.info("Saving enriched data...")
    enriched_data.to_csv('bertopic_tm_v2.csv', index=False)
    bertopic_model.save("bertopic_model", serialization="pickle")

    logging.info("Processing complete.")

if __name__ == "__main__":
    main()
