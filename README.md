# NounsAI Data Pipeline

Pipeline to build the Q&A database that Roko leverages to answer questions.

## Table of Contents

- [Installation](#installation)
- [Usage](#usage)

## Installation

### Prerequisites

1. Ensure you have `gzip` utility installed on your machine to decompress the database file.
2. You need to have PostgreSQL installed and running. If you don't have it installed, you can download it from [here](https://www.postgresql.org/download/).

### Setup

1. **Clone the repository**:

   ```
   git clone https://github.com/nounsai/data-pipeline
   cd data-pipeline
   ```

   > **Note:** Replace `YOUR_GITHUB_USERNAME` with your actual GitHub username.

2. **Decompress the database file**:

   Navigate to the `db/` directory:

   ```
   cd db/
   ```

   Decompress the file:

   ```
   gzip -d nounsai_db.sql.gz
   ```

3. **Import the SQL file into PostgreSQL**:

   First, create a new PostgreSQL database for the project (you can name it as you like, for this example we'll name it `nounsai_db`):

   ```
   createdb nounsai_db
   ```

   Now, import the decompressed SQL file into the database:

   ```
   psql nounsai_db < nounsai_db.sql
   ```

4. **Navigate to Docker setup**:

   Move to the `qa/docker` directory:

   ```
   cd ../qa/docker/
   ```

   Here you'll find the Dockerfile and related programs for the Q&A processing pipeline.

## Usage

Run `qa/docker/main.py` on a scheduler of your choice.
