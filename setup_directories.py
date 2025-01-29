import os

# Define the directory structure
directories = [
    "agency_divisions/planning/tools",
    "agency_divisions/planning/data",
    "agency_divisions/planning/docs",
    "agency_divisions/planning/agents",
    "agency_divisions/internal_operations/tools",
    "agency_divisions/internal_operations/data",
    "agency_divisions/internal_operations/docs",
    "agency_divisions/internal_operations/agents",
    "agency_divisions/analysis/tools",
    "agency_divisions/analysis/data",
    "agency_divisions/analysis/docs",
    "agency_divisions/analysis/agents",
    "agency_divisions/projects/tools",
    "agency_divisions/projects/data",
    "agency_divisions/projects/docs",
    "agency_divisions/projects/agents",
]

# Create directories
for directory in directories:
    os.makedirs(directory, exist_ok=True)
    print(f"Created directory: {directory}")

print("\nDirectory structure setup complete!") 