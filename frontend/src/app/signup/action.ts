"use server";

import { z } from "zod";
import { redirect } from "next/navigation";

//validation
export const SignupFormSchema = z.object({
    firstName: z
      .string()
      .min(2, { message: 'First name must be at least 2 characters long.' })
      .trim(),
    lastName: z
      .string() 
      .min(2, { message: 'Last name must be at least 2 characters long.' })
      .trim(),
    email: z
      .string()
      .email({ message: 'Please enter a valid email.' })
      .trim()
      .toLowerCase(),
    password: z
      .string()
      .min(12, { message: 'Password must be at least 12 characters long' })
      .regex(/[a-z]/, { message: 'Password must contain at least one lowercase letter' })
      .regex(/[A-Z]/, { message: 'Password must contain at least one uppercase letter' })
      .regex(/[0-9]/, { message: 'Password must contain at least one number' })
      .regex(/[^a-zA-Z0-9]/, { message: 'Password must contain at least one special character' })
      .trim(),
    confirmPassword: z
      .string()
      .min(1, { message: 'Password confirmation is required' })
      .trim(),
  }).refine((data) => data.password === data.confirmPassword, {
    message: "Passwords don't match",
    path: ["confirmPassword"],
  })

export type FormState =
  | {
      errors?: {
        name?: string[]
        email?: string[]
        password?: string[]
        confirmPassword?: string[]
      }
      message?: string
    }
  | undefined


export async function signup(formData: FormData) {


}

