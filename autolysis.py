# /// script
# requires-python = ">=3.8"
# dependencies = [
#   "pandas",
#   "seaborn",
#   "matplotlib",
#   "numpy",
#   "scikit-learn",
#   "scipy",
#   "requests",
# ]
# ///

# Import necessary libraries
import os
import sys
import json
import requests
import pandas as pd
import seaborn as sns
import matplotlib.pyplot as plt
import numpy as np
from sklearn.mixture import GaussianMixture
from scipy.stats import lognorm
from sklearn.feature_extraction.text import CountVectorizer
from sklearn.decomposition import LatentDirichletAllocation

# Set environment variable for API proxy token
os.environ["AIPROXY_TOKEN"] = "eyJhbGciOiJIUzI1NiJ9.eyJlbWFpbCI6IjIyZjIwMDA3NjFAZHMuc3R1ZHkuaWl0bS5hYy5pbiJ9.7Dtl6da2qqHT0vQFVFQjFjlpiSllXpYIOZZPlHqFSds"

# Define the main class for data analysis
class DataAnalysisTool:
    def __init__(self, data_path: str):
        """
        Initialize the tool with the dataset path.
        Load the dataset and validate the presence of API proxy token.
        """
        self.data_path = data_path
        self.df = pd.read_csv(data_path, encoding='latin-1')
        self.ai_proxy_token = os.environ.get("AIPROXY_TOKEN")
        if not self.ai_proxy_token:
            raise ValueError("AIPROXY_TOKEN environment variable not set")

        self.api_url = "http://aiproxy.sanand.workers.dev/openai/v1/chat/completions"

    def perform_statistical_analysis(self) -> dict:
        """
        Perform statistical analysis on the dataset.
        Extract numeric columns, summarize the data, and return analysis details.
        """
        print("[INFO] Performing statistical analysis...")
        numeric_data = self.df.select_dtypes(include=['number'])
        analysis_details = {
            "columns": self.df.columns.tolist(),
            "data_types": self.df.dtypes.astype(str).to_dict(),
            "summary_statistics": self.df.describe(include='all').to_dict(),
            "missing_data": self.df.isna().sum().to_dict(),
        }
        return numeric_data, analysis_details

    def create_visualizations(self, numeric_data: pd.DataFrame, output_path: str):
        """
        Create visualizations such as correlation heatmaps, histograms, and model fits.
        Save visualizations to the specified output path.
        """
        print("\n[INFO] Creating visualizations...")
        os.makedirs(output_path, exist_ok=True)

        numeric_columns = numeric_data.columns

        # Create a correlation heatmap if there are multiple numeric columns
        if len(numeric_columns) > 1:
            plt.figure(figsize=(9, 7))
            sns.heatmap(numeric_data.corr(), annot=True, cmap="viridis")
            plt.title("Correlation Matrix")
            plt.savefig(os.path.join(output_path, "heatmap_correlation.png"))
            plt.close()

        # Create a histogram and model fits for the first numeric column
        if len(numeric_columns) > 0:
            first_numeric = numeric_columns[0]
            data_col = self.df[first_numeric]

            plt.figure(figsize=(8, 6))
            sns.histplot(data_col, kde=True, bins=30, color="blue", label="Histogram + KDE")
            plt.title(f"Distribution of {first_numeric}")

            # Fit Gaussian Mixture Model (GMM)
            gmm = GaussianMixture(n_components=2, random_state=0)
            gmm.fit(data_col.dropna().values.reshape(-1, 1))
            x_vals = np.linspace(data_col.min(), data_col.max(), 1000).reshape(-1, 1)
            gmm_pdf = np.exp(gmm.score_samples(x_vals))
            plt.plot(x_vals, gmm_pdf, label="Gaussian Mixture Model", linestyle='--')

            # Fit Log-Normal Distribution
            shape, loc, scale = lognorm.fit(data_col.dropna())
            pdf = lognorm.pdf(x_vals.ravel(), shape, loc=loc, scale=scale)
            plt.plot(x_vals, pdf, label="Log-Normal Distribution", linestyle='-.')

            plt.legend()
            plt.savefig(os.path.join(output_path, f"{first_numeric}_distribution_with_models.png"))
            plt.close()

    def perform_lda_analysis(self, num_topics: int = 5) -> dict:
        """
        Perform Latent Dirichlet Allocation (LDA) for topic modeling on text columns.
        Extracts topics for each text column and returns the results.
        """
        text_columns = self.df.select_dtypes(include=['object', 'category']).columns
        lda_results = {}

        for column in text_columns:
            print(f"Performing LDA on column: {column}")
            vectorizer = CountVectorizer(stop_words='english')
            data_vectorized = vectorizer.fit_transform(self.df[column].dropna())

            lda = LatentDirichletAllocation(n_components=num_topics, random_state=42)
            lda.fit(data_vectorized)

            topics = []
            for topic_idx, topic in enumerate(lda.components_):
                topic_terms = [vectorizer.get_feature_names_out()[i] for i in topic.argsort()[:-10 - 1:-1]]
                topics.append(f"Topic {topic_idx + 1}: {' '.join(topic_terms)}")

            lda_results[column] = topics

        return lda_results

    def generate_narrative(self, analysis_results: dict, lda_results: dict) -> str:
        """
        Generate a narrative report summarizing analysis and LDA results using GPT.
        Sends a prompt to an AI model and retrieves the generated content.
        """
        prompt = f"""
        Write a detailed analysis of this dataset, covering:
        - Statistical summary and visualization insights.
        - Key findings from the LDA topic modeling.
        Dataset Summary:
        {json.dumps(analysis_results, indent=2)}
        LDA Results:
        {json.dumps(lda_results, indent=2)}
        """

        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {self.ai_proxy_token}"
        }

        payload = {
            "model": "gpt-4o-mini",
            "messages": [{"role": "user", "content": prompt}]
        }

        try:
            print("Requesting GPT analysis...")
            response = requests.post(self.api_url, headers=headers, json=payload)

            if response.status_code == 200:
                data = response.json()
                return data.get('choices', [{}])[0].get('message', {}).get('content', 'No content available')
            else:
                print(f"Error: {response.status_code} - {response.text}")
                return "Error generating narrative."
        except Exception as e:
            print(f"Error generating narrative: {e}")
            return "Error generating narrative."

    def execute(self):
        """
        Main execution pipeline:
        1. Perform statistical analysis.
        2. Create visualizations.
        3. Perform LDA analysis.
        4. Generate narrative report.
        Save results to an output folder.
        """
        numeric_data, analysis_details = self.perform_statistical_analysis()
        output_path = os.path.splitext(self.data_path)[0] + "_results"
        self.create_visualizations(numeric_data, output_path)

        lda_results = self.perform_lda_analysis()
        narrative = self.generate_narrative(analysis_details, lda_results)

        with open(os.path.join(output_path, "analysis_report.md"), "w", encoding="utf-8") as file:
            file.write(narrative)

        print(f"Analysis completed. Results saved to {output_path}")

# Define the main entry point for the script
def main():
    if len(sys.argv) != 2:
        print("Usage: python analyze_data.py <dataset.csv>")
        sys.exit(1)

    data_path = sys.argv[1]
    if not os.path.exists(data_path):
        print(f"Error: File '{data_path}' not found.")
        sys.exit(1)

    analyzer = DataAnalysisTool(data_path)
   

describe the code in commesnts abt the analysis 
