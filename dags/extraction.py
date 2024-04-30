import requests
import pandas as pd
import time
import json
from datetime import datetime, timezone
import os
import logging

# Set up logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

def get_steam_reviews(appid, max_reviews=100000, retries=5):
    """
    Fetches up to a specified number of reviews for a game on Steam, extracting key data points for analysis.

    Parameters:
        appid (str): The Steam Application ID for the game.
        max_reviews (int): Maximum number of reviews to fetch.
        retries (int): Number of retries for API requests.

    Returns:
        list of dict: A list of dictionaries, each containing key details about a review.
    """
    reviews_list = []
    cursor = '*'
    url = f"https://store.steampowered.com/appreviews/{appid}"

    while len(reviews_list) < max_reviews and retries > 0:
        try:
            params = {
                "cursor": cursor,
                "json": 1,
                "filter": "recent",
                "num_per_page": 100,
                "language": "english"
            }
            response = requests.get(url, params=params)
            response.raise_for_status()
            data = response.json()

            if 'reviews' not in data or not data['reviews']:
                break

            for review in data['reviews']:
                review_details = {
                    'recommendation_id': review.get('recommendationid'),
                    'steamid': review['author']['steamid'],
                    'num_reviews': review['author']['num_reviews'],
                    'playtime_forever': review['author']['playtime_forever'],
                    'playtime_at_review': review['author'].get('playtime_at_review', None),
                    'language': review['language'],
                    'review_text': review['review'],
                    'timestamp_created': datetime.fromtimestamp(review['timestamp_created'], tz=timezone.utc).strftime('%Y-%m-%d %H:%M:%S'),
                    'voted_up': review['voted_up'],
                    'votes_up': review['votes_up'],
                    'votes_funny': review['votes_funny'],
                    'weighted_vote_score': review.get('weighted_vote_score'),
                }
                reviews_list.append(review_details)

            cursor = data.get('cursor', '')
            if cursor == '':
                break

            time.sleep(5)

        except requests.RequestException as e:
            retries -= 1
            logging.error(f"Request failed: {e}, retrying... ({retries} retries left)")
            time.sleep(10)
        except KeyError as e:
            logging.error(f"Key error: {e} - possible change in data format or data is missing.")
            break

    return reviews_list[:max_reviews]


def search_steam_games(query):
    """
    Searches for Steam games by query and filters out non-main games (like DLCs and expansions).

    Parameters:
        query (str): Search query for the game.

    Returns:
        list of dict: A list of dictionaries, each containing key details about a game.
    """
    search_url = f"https://store.steampowered.com/api/storesearch/?term={query}&cc=US&l=english"
    search_response = requests.get(search_url)
    search_results = search_response.json()

    games = []
    if 'items' in search_results:
        for item in search_results['items']:
            name = item['name']
            if "call of duty" in name.lower() and 'dlc' not in name.lower() and 'pack' not in name.lower() and 'expansion' not in name.lower():
                appid = int(item['id'])
                hover_url = f"https://store.steampowered.com/apphoverpublic/{appid}?l=english&json=1"
                hover_response = requests.get(hover_url)
                hover_data = hover_response.json()

                # Extract ReviewSummary data
                review_summary = hover_data.get('ReviewSummary', None)
                summary_text = review_summary.get('strReviewSummary', None)
                review_count = review_summary.get('cReviews', 0)
                positive_reviews = review_summary.get('cRecommendationsPositive', None)
                negative_reviews = review_summary.get('cRecommendationsNegative', None)
                review_score = review_summary.get('nReviewScore', None)

                games.append({
                    'game_name': name,
                    'app_id': appid,
                    'release_date': hover_data.get('strReleaseDate', None),
                    'review_summary': summary_text,
                    'review_count': review_count,
                    'positive_review_count': positive_reviews,
                    'negative_review_count': negative_reviews,
                    'review_score': review_score
                })
    return games


def main():
    logging.info("Starting game data extraction...")
    games = search_steam_games("helldivers 2")
    if games:
        logging.info(f"Found {len(games)} games. Processing reviews...")
        all_reviews_list = []

        for game in games:
            appid = game['app_id']
            try:
                reviews = get_steam_reviews(appid)
                for review in reviews:
                    review.update({
                        'game_name': game['game_name'],
                        'app_id': game['app_id']
                    })
                    all_reviews_list.append(review)
            except Exception as e:
                logging.error(f"Failed to fetch or process data for app_id {appid}: {e}")

        all_reviews_df = pd.DataFrame(all_reviews_list)
        all_reviews_df.to_csv('steam_reviews.csv', index=False)
        logging.info("Reviews data saved to 'steam_reviews.csv'.")
    else:
        logging.warning("No games found for the provided query.")

if __name__ == "__main__":
    main()
