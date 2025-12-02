# Ticket Assigner Automation

A lightweight Python-based automation that fetches incoming support tickets from an API,
applies custom assignment logic, and distributes the tickets to team members based on
predefined rules. This automation reduces manual effort, improves fairness in ticket
distribution, and ensures faster response times.

## 🔧 How It Works

- The script pulls ticket data from an external API.
- Reads team member information from a JSON file stored in S3.
- Applies assignment logic (round robin / load-based / priority-based depending on rules).
- Updates the assigned owner for each ticket through the API.

This project was built to streamline internal workflow operations and ensure smooth
ticket distribution across the support team.

## 📁 Project Structure
```
ticket-assigner-automation/
│
├── main.py # Main Python script for ticket fetching and assignment
├── teammates.json # Team member metadata (sample/mock)
├── README.md # Project documentation
└── .gitignore # Standard gitignore
```


## ▶️ Running the Script

Update `teammates.json` if needed, then run:

You may need environment variables such as:
export API_KEY="xxxxxxx-xxxxxx-xxxxx"
export BASE_URL="xxxxxxx-xxxxxx-xxxxx"



## 📄 teammates.json (example)
[
{"name": "John", "capacity": 10},
{"name": "Sara", "capacity": 8},
{"name": "Ravi", "capacity": 12}
]


## ✨ Features

- Automates ticket assignment
- Removes manual work in distributing support tasks
- Ensures fair and consistent allocation using defined rules
- Can be extended with:
  - Load balancing
  - Priority rules
  - Email/SNS notification

## 🚀 Future Enhancements (optional)

- Add AWS Lambda deployment
- Add CloudWatch scheduled trigger
- Store assignment logs in S3
- Add retry and error handling

