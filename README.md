# SmartCart - Retail Analytics Platform

A production-level Flask application for analyzing retail sales data using machine learning and association rule mining.

## Features

- **User Authentication**: Secure login and registration system
- **Data Upload**: Support for simple CSV and complex datasets (Instacart format)
- **Smart Data Processing**: 
  - Automatic data cleaning and validation
  - Context enrichment (time of day, budget segments, basket sizes)
  - Duplicate removal and error correction
- **Association Rule Mining**: Apriori algorithm implementation
- **Analytics Dashboard**: 
  - Interactive charts and visualizations
  - Transaction statistics
  - Product performance metrics
- **Context-Aware Recommendations**: Filter by time, budget, and basket size
- **Multi-Upload Support**: Manage multiple datasets

## Technology Stack

- **Backend**: Flask 2.3.3
- **Database**: SQLAlchemy with SQLite (dev) / PostgreSQL (production)
- **Authentication**: Flask-Login
- **Data Processing**: Pandas, NumPy
- **Machine Learning**: MLxtend (Apriori algorithm)
- **Visualization**: Chart.js, Matplotlib, Seaborn
- **Frontend**: Bootstrap 5, HTML5, CSS3

## Installation

### Prerequisites

- Python 3.8+
- pip
- Virtual environment (recommended)

### Setup

1. **Clone the repository**
   ```bash
   cd /Users/cyrilmugada/Documents/market/smartcart
   ```

2. **Create virtual environment**
   ```bash
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   ```

3. **Install dependencies**
   ```bash
   pip install -r requirements.txt
   ```

4. **Configure environment**
   ```bash
   cp .env.example .env
   # Edit .env with your configuration
   ```

5. **Initialize database**
   ```bash
   flask init-db
   ```

6. **Run the application**
   ```bash
   python run.py
   ```

   The application will be available at `http://localhost:5000`

## Usage

### 1. Register and Login
- Create a new account with your store name
- Login with your credentials

### 2. Upload Data
- Navigate to "Upload Data"
- Select data type (Simple CSV or Complex)
- Upload your CSV file

**Simple CSV Format:**
```
order_id,product_id,product_name
1,101,Bread
1,102,Butter
2,101,Bread
2,103,Milk
```

### 3. View Analytics
- Check upload history
- View detailed analytics for each upload
- Explore charts and statistics

### 4. Get Recommendations
- Select a product
- Filter by context (time, budget, basket size)
- View product recommendations with confidence metrics

## Project Structure

```
smartcart/
├── app/
│   ├── __init__.py              # Application factory
│   ├── models.py                # Database models
│   ├── forms.py                 # WTForms forms
│   ├── routes.py                # Flask routes
│   ├── analytics_engine.py       # Analytics logic
│   └── templates/
│       ├── base.html            # Base template
│       ├── index.html           # Home page
│       ├── auth/
│       │   ├── login.html
│       │   └── register.html
│       └── dashboard/
│           ├── overview.html
│           ├── upload.html
│           ├── upload_history.html
│           ├── analytics_detail.html
│           └── recommendations.html
├── config.py                    # Configuration
├── run.py                       # Application entry point
├── requirements.txt             # Dependencies
├── .env.example                 # Environment template
└── README.md                    # This file
```

## Configuration

### Development
```bash
FLASK_ENV=development
DEBUG=True
SQLALCHEMY_DATABASE_URI=sqlite:///smartcart_dev.db
```

### Production
```bash
FLASK_ENV=production
DEBUG=False
SQLALCHEMY_DATABASE_URI=postgresql://user:password@host/smartcart
```

## Analytics Engine

### Data Processing Pipeline

1. **Load & Validate**: CSV validation and structure checking
2. **Clean**: Remove duplicates, handle missing values
3. **Enrich**: Add context (time, budget, basket size)
4. **Analyze**: Generate association rules using Apriori
5. **Store**: Save results to database

### Association Rules

The system generates rules with three key metrics:

- **Support**: How often items appear together
- **Confidence**: Probability of consequent given antecedent
- **Lift**: Strength of association vs. random chance

### Context Dimensions

- **Time of Day**: Morning, Afternoon, Evening, Night
- **Budget Segment**: Low, Medium, High
- **Basket Size**: Small, Medium, Large

## API Endpoints

### Authentication
- `POST /auth/register` - Register new user
- `POST /auth/login` - Login user
- `GET /auth/logout` - Logout user

### Dashboard
- `GET /dashboard/overview` - Dashboard overview
- `GET /dashboard/upload` - Upload page
- `POST /dashboard/upload` - Process upload
- `GET /dashboard/upload-history` - View uploads
- `GET /dashboard/analytics/<upload_id>` - View analytics
- `GET /dashboard/recommendations` - Recommendations page

### API
- `GET /api/recommendations/<product_id>` - Get recommendations
- `GET /api/analytics/<upload_id>` - Get analytics data

## Database Models

### User
- Retailer account information
- Store name and contact details

### DataUpload
- Upload metadata and status
- File information and processing status

### Analytics
- Aggregated analytics results
- Distribution statistics

### AssociationRule
- Generated association rules
- Support, confidence, lift metrics

### Product
- Product catalog
- Performance metrics

### Transaction
- Individual transactions
- Context information

## Performance Considerations

- **Adaptive Thresholds**: Automatically adjusts Apriori parameters based on dataset size
- **Efficient Processing**: Optimized for datasets up to 100MB
- **Database Indexing**: Strategic indexes on frequently queried columns
- **Caching**: Results cached in database for quick retrieval

## Security Features

- Password hashing with Werkzeug
- CSRF protection with Flask-WTF
- SQL injection prevention with SQLAlchemy ORM
- Secure session cookies
- User isolation (users only see their own data)

## Deployment

### Using Gunicorn (Production)

```bash
pip install gunicorn
gunicorn -w 4 -b 0.0.0.0:5000 run:app
```

### Using Docker

```dockerfile
FROM python:3.9-slim
WORKDIR /app
COPY requirements.txt .
RUN pip install -r requirements.txt
COPY . .
CMD ["gunicorn", "-w", "4", "-b", "0.0.0.0:5000", "run:app"]
```

### Environment Variables for Production

```bash
FLASK_ENV=production
SECRET_KEY=<generate-secure-key>
DATABASE_URL=postgresql://user:password@host/smartcart
```

## Troubleshooting

### Database Issues
```bash
# Reset database
flask drop-db
flask init-db
```

### Upload Errors
- Check CSV format matches requirements
- Ensure file size < 100MB
- Verify column names are correct

### Performance Issues
- Reduce dataset size for testing
- Increase Apriori support threshold
- Use PostgreSQL for production

## Future Enhancements

- [ ] Async task processing with Celery
- [ ] Advanced visualization options
- [ ] Export reports to PDF/Excel
- [ ] Real-time data streaming
- [ ] Machine learning model improvements
- [ ] Mobile app support
- [ ] API rate limiting
- [ ] Advanced user roles and permissions

## Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Submit a pull request

## License

MIT License - See LICENSE file for details

## Support

For issues and questions, please create an issue in the repository.

## Author

SmartCart Development Team

## Changelog

### Version 1.0.0 (Initial Release)
- User authentication system
- CSV data upload and processing
- Association rule mining
- Analytics dashboard
- Product recommendations
- Context-aware filtering

[![Review Assignment Due Date](https://classroom.github.com/assets/deadline-readme-button-22041afd0340ce965d47ae6ef1cefeee28c7c493a6346c4f15d667ab976d596c.svg)](https://classroom.github.com/a/l6edej4a)
[![Open in Visual Studio Code](https://classroom.github.com/assets/open-in-vscode-2e0aaae1b6195c2367325f4f02e2d04e9abb55f0b24a779b69b11b9e10269abc.svg)](https://classroom.github.com/online_ide?assignment_repo_id=19902931&assignment_repo_type=AssignmentRepo)
