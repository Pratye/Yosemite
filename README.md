# Yosemite - AI-Driven Consumer Insights Platform

Welcome to **Yosemite**, an AI-powered platform designed to help consumers make informed choices by providing real-time insights on food products. This project was developed as part of the **ConsumeWise** challenge for the **Gen AI Exchange Hackathon by Google**. 

## 🌐 Live Demo
Check out the live application at: [www.thirdeye.website](http://www.thirdeye.website)
<br> Wait for a few seconds for the server to start. It is hosted on Google Cloud Run.</br>

## 🚀 Project Overview
Yosemite is an AI-enabled smart platform that:
- Automatically collects data from food product labels using **OCR (Google Document AI)** and **LangChain** for web scraping.
- Extracts and analyzes key nutritional data, ingredients, proprietary claims (e.g., sugar-free, trans fat-free), and other relevant information.
- Leverages multiple **open-source food databases** like **Open Food Facts** and **FoodData Central** to provide accurate, comprehensive data.
- Uses **GenAI** to perform health analysis, validate product claims, and generate personalized nudges for consumers based on their dietary preferences.
- Ensures a scalable, low-latency experience by utilizing **Google Cloud Run GPU** for real-time processing.

## 🛠️ Features
- **Data Scraping**: Extracts information from food labels, websites, and databases.
- **ETL Pipeline**: Organizes, standardizes, and validates the collected data.
- **AI-Powered Health Analysis**: Provides health insights on ingredients, nutritional values, and proprietary claims.
- **Personalized Insights**: Recommends healthier alternatives and alerts users to potential allergens or harmful ingredients.
- **Multi-Source Integration**: Supports data from Open Food Facts, FoodData Central, Edamam Food Database, and more.

## 💡 How it Works
1. **Data Collection**: Yosemite scrapes and processes product data from multiple sources using **LangChain** and **OCR** technology.
2. **ETL Pipeline**: The data is extracted, transformed, and loaded into a structured format.
3. **AI-Powered Analysis**: The platform uses **GenAI** to analyze the data and provide insights.
4. **User Interaction**: Consumers can interact with the platform through a chatbot interface to get real-time health recommendations and insights.

## 🔧 Tech Stack
- **Python**
- **Flask** (Backend)
- **LangChain** (Web Scraping)
- **Google Document AI** (OCR)
- **FAISS Vector DB** (Database)
- **Google Cloud Run GPU** (Deployment)
- **GenAI** (AI-powered health analysis)

## 🖥️ Architecture Overview
- **User Interface**: Chatbot that provides real-time product insights and recommendations.
- **Data Collection**: Scrapes and collects data from food labels and external sources.
- **ETL Pipeline**: Standardizes and processes data for analysis.
- **Database**: Stores processed data using FAISS Vector DB.
- **AI-Powered Analysis**: Analyzes product data to generate personalized insights.
- **Integration**: Multi-source support for data validation and enrichment.

## 🔍 Features in Development
- **Multi-Language Support**: Extending insights for consumers in various languages.
- **New Product Integration**: Continuous data scraping for new products in the market.
- **Mobile-Friendly Interface**: Expanding to mobile platforms for broader accessibility.

## 📄 License
This project is licensed under the **Creative Commons Attribution-NonCommercial-NoDerivatives 4.0 International License** (CC BY-NC-ND 4.0). You can view the full terms in the [LICENSE](LICENSE) file.

### Key Terms:
- **Attribution**: You must give appropriate credit by linking to this repository and citing the original author.
- **NonCommercial**: This code cannot be used for commercial purposes.
- **NoDerivatives**: Modifications or derivative works cannot be distributed without explicit permission.

For any contributions, please seek prior approval from the original author.


## 📧 Contact
For more information or queries, please reach out at **[pratye.aggarwal@gmail.com](mailto:pratye.aggarwal@gmail.com)**.

---

**ConsumeWise Challenge** | **Gen AI Exchange Hackathon by Google**
