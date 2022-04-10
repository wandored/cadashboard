"""
import csv file with POS - recipe links and
write to database
"""
import os
from sqlalchemy.engine.create import create_engine
import pandas as pd
import psycopg2
from dashapp import Config


def removedups(x):
    """Turn the list into a dict then back to a list to remove duplicates"""
    return list(dict.fromkeys(x))


if __name__ == "__main__":

    engine = create_engine(Config.SQLALCHEMY_DATABASE_URI)
    conn = psycopg2.connect(
        host="localhost",
        database="dashboard",
        user=Config.PSYCOPG2_USER,
        password=Config.PSYCOPG2_PASS,
    )
    cur = conn.cursor()

    df = pd.read_csv("/tmp/export.csv", sep=",")
    df.loc[:, "Name"] = df["Name"].str.replace(
        r"CHOPHOUSE - NOLA", "CHOPHOUSE-NOLA", regex=True
    )
    df.loc[:, "Name"] = df["Name"].str.replace(r"CAFÉ", "CAFE", regex=True)
    df.loc[:, "Name"] = df["Name"].str.replace(r"^(?:.*?( -)){2}", "-", regex=True)
    df[["name", "menuitem"]] = df["Name"].str.split(" - ", expand=True)
    df.drop(columns=["Name", "__count", "Barcode"], inplace=True)
    df.rename(
        columns={
            "RecipeId": "recipeid",
            "Recipe": "recipe",
            "Category1": "category1",
            "Category2": "category2",
            "POSID": "posid",
            "MenuItemId": "menuitemid",
        },
        inplace=True,
    )
    df = df[
        [
            "name",
            "menuitem",
            "recipe",
            "category1",
            "category2",
            "posid",
            "recipeid",
            "menuitemid",
        ]
    ]

    print(df.info())

    df_cost = pd.read_csv(
        "/usr/local/share/Menu Price Analysis.csv", skiprows=3, sep=",", thousands=","
    )
    df_cost.loc[:, "MenuItemName"] = df_cost["MenuItemName"].str.replace(
        r"CHOPHOUSE - NOLA", "CHOPHOUSE-NOLA", regex=True
    )
    df_cost.loc[:, "MenuItemName"] = df_cost["MenuItemName"].str.replace(
        r"CAFÉ", "CAFE", regex=True
    )
    df_cost.loc[:, "MenuItemName"] = df_cost["MenuItemName"].str.replace(
        r"^(?:.*?( -)){2}", "-", regex=True
    )
    df_cost[["name", "menuitem"]] = df_cost["MenuItemName"].str.split(
        " - ", expand=True
    )

    df_cost.drop(
        columns=[
            "AvgPrice1",
            "Profit1",
            "Textbox35",
            "TargetMargin1",
            "Textbox43",
            "PriceNeeded1",
            "Location",
            "Cost1",
            "AvgPrice",
            "Profit",
            "ProfitPercent",
            "TargetMargin",
            "Variance",
            "PriceNeeded",
            "MenuItemName",
        ],
        inplace=True,
    )
    df_cost.rename(columns={"Cost": "cost"}, inplace=True)
    df_cost = df_cost[["name", "menuitem", "cost"]]

    recipes = pd.merge(df_cost, df, on=["name", "menuitem"], how="left")
    # Need to fix names to match the database
    recipes.loc[:, "name"] = recipes["name"].str.replace(
        r"'47", "47", regex=True
    )
    recipes.loc[:, "name"] = recipes["name"].str.replace(r"NEW YORK PRIME-BOCA", "NYP-BOCA", regex=True)
    recipes.loc[:, "name"] = recipes["name"].str.replace(r"NEW YORK PRIME-MYRTLE BEACH", "NYP-MYRTLE BEACH", regex=True)
    recipes.loc[:, "name"] = recipes["name"].str.replace(r"NEW YORK PRIME-ATLANTA", "NYP-ATLANTA", regex=True)
    print(recipes)

    #    cur.execute('DELETE FROM "Recipes"')
    #    conn.commit()
    #
    recipes.to_sql("Recipes", engine, if_exists="replace", index_label='id')
    conn.commit()

    conn.close()
