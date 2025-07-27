import 'server-only'
import { SignJWT, jwtVerify } from 'jose'
//import { SessionPayload } from '@/app/lib/definitions'
import { cookies } from 'next/headers'
import { v4 as uuidv4 } from 'uuid'

type SessionPayload = {
    userId: string
    expiresAt: Date
}

const secretKey = process.env.SESSION_SECRET
const encodedKey = new TextEncoder().encode(secretKey)

export async function encrypt(payload: SessionPayload) {
    return new SignJWT(payload)
      .setProtectedHeader({ alg: 'HS256' })
      .setIssuedAt()
      .setExpirationTime('1d')
      .sign(encodedKey)
  }
   
export async function decrypt(session: string | undefined = '') {
    try {
      const { payload } = await jwtVerify(session, encodedKey, {
        algorithms: ['HS256'],
      })
      return payload
    } catch (error) {
      console.log('Failed to verify session')
    }
  }

export function genereateSessionID() {
    return crypto.randomUUID()
}

export async function createSession(userId: string) {
    //expire en un jour
    const expiresAt = new Date(Date.now() + 24 * 60 * 60 * 1000)
    const session = await encrypt({ userId, expiresAt })
    const cookieStore = await cookies()
   
    cookieStore.set('session', session, {
      httpOnly: true,
      secure: true,
      expires: expiresAt,
      sameSite: 'lax',
      path: '/',
    })
  }
