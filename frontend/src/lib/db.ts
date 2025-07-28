import mongoose from "mongoose";
import { MongoClient } from "mongodb";
import dotenv from "dotenv";
dotenv.config();

const connectDB = async () => {
  try {
    const MONGODB_URI = process.env.MONGODB_URI!;

    if (!MONGODB_URI) {
      throw new Error("Please define the MONGODB_URI environment variable");
    }
    await mongoose.connect(MONGODB_URI);
    console.log("Connected to MongoDB");
  } catch (error) {
    console.error("Failed to connect to MongoDB:", error);
    throw error;
  }
};

export default connectDB;
