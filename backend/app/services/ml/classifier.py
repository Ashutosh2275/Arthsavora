import os
import joblib
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.naive_bayes import MultinomialNB
from sklearn.pipeline import Pipeline

# Large-scale Synthetic Dataset for Production Generalization
DATASET = [
    # FOOD & DINING
    ("zomato swiggy starbucks kfc mcdonalds pizza hut dominos cafe coffee day", "Food"),
    ("restaurant dining lunch dinner breakfast burger king subway taco bell", "Food"),
    ("bakery cake sweets mithai bar kitchen grill pub brewery bar", "Food"),
    ("blinkit zepto bigbasket milk basket grocery vegetables fruits", "Food"),
    
    # TRAVEL & TRANSPORT
    ("uber ola rapido taxi cab booking irctc railway indian railways", "Travel"),
    ("indigo air india spicejet vistara flight ticket airport parking", "Travel"),
    ("petrol shell hpcl bpcl fuel diesel cng auto rickshaw bus fare", "Travel"),
    ("makemytrip goibibo agoda redbus booking travel agency toll plaza fastag", "Travel"),
    
    # SHOPPING
    ("amazon flipkart myntra zara h&m hnm pantaloons lifestyle max fashion", "Shopping"),
    ("reliance digital croma vijay sales apple store electronics gadget", "Shopping"),
    ("nike adidas decathlon sports shoes clothing apparel mall central", "Shopping"),
    ("nykaa purplle sephora cosmetic beauty pharmacy medplus apollo pharmacy", "Shopping"),
    
    # BILLS & UTILITIES
    ("jio airtel vi recharge mobile prepaid postpaid broadband wifi", "Bills"),
    ("electricity bill bescom cesc power water board gas cylinder hpgas", "Bills"),
    ("tata play dth subscription insurance premium lic policy paytm bill", "Bills"),
    
    # ENTERTAINMENT
    ("netflix prime video disney hotstar youtube premium spotify music", "Bills"),
    ("pvr inox bookmyshow cinema movie theatre multiplex theme park club", "Entertainment"),
    ("steam playstation xbox nintendo gaming lounge twitch discord", "Entertainment"),
    
    # HEALTH
    ("hospital clinic doctor consultation dentist lab reports diagnostic", "Health"),
    ("pharmacy medicine apollo medplus firstaid surgery medical insurance", "Health"),
    
    # HOUSING
    ("rent apartment maintenance security society deposit plumber electrician", "Housing"),
    ("furniture ikea wakefit home decor hardware asian paints painting", "Housing")
]

MODEL_PATH = "expense_model.joblib"

class ExpenseCategorizer:
    def __init__(self):
        # We use Tfidf (more advanced than CountVectorizer)
        self.model = Pipeline([
            ('tfidf', TfidfVectorizer(ngram_range=(1, 2))), # Looks for single words and pairs
            ('clf', MultinomialNB(alpha=0.1)) # Optimized for smaller datasets
        ])
        self.train_and_save()

    def train_and_save(self):
        """Trains the model and saves it to a file for persistence"""
        X, y = zip(*DATASET)
        self.model.fit(X, y)
        joblib.dump(self.model, MODEL_PATH)
        print("LOG: AI Categorizer Model Trained and Persistent.")

    def predict(self, description: str):
        if not description or len(description) < 2:
            return "Shopping"
        
        # Load model if it exists, else use current memory
        if os.path.exists(MODEL_PATH):
            loaded_model = joblib.load(MODEL_PATH)
            prediction = loaded_model.predict([description.lower()])
        else:
            prediction = self.model.predict([description.lower()])
            
        return str(prediction[0])

# Global instance for the app
ai_categorizer = ExpenseCategorizer()