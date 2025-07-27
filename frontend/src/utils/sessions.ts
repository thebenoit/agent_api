import { jwtDecode } from "jwt-decode";

const logout = () => {
    sessionStorage.removeItem('auth');
}
const setToken = (token: string) => {
    sessionStorage.setItem('auth', token);
}
const getToken = () => {
    return sessionStorage.getItem('auth');
}
const decodeToken = () => {
    const token = getToken();
    if (token) {
        try {
            return jwtDecode(token);
        } catch (error) {
            console.error('Error decoding token:', error);
            return null;
        }
    }
    return null;
}
// const getUserId = () => {
//     const decoded = decodeToken();
//     return decoded ? decoded.userId : null;
// },
// const getEmail = () => {
//     const decoded = decodeToken();
//     return decoded ? decoded.email : null;
// }

export { logout, setToken, getToken, decodeToken };
