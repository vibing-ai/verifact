import os
from supabase import create_client, Client

# Load environment variables
SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_KEY")

supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)

def insert_claim(content):
    response = supabase.table("claims").insert({"content": content}).execute()
    print(response.data)

def get_all_claims():
    response = supabase.table("claims").select("*").execute()
    print(response.data)

def delete_all_claims():
    response = supabase.table("claims").delete().gt("id", 0).execute()
    print(response.data)

if __name__ == "__main__":
    delete_all_claims()
    insert_claim("The earth revolves around the sun.")
    # insert_claim("Water boils at 100 degrees Celsius at sea level.")
    # get_all_claims()
    get_all_claims()