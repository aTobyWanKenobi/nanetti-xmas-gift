import { useState } from "react";
import { motion } from "framer-motion";

export default function Login({ onLogin }) {
    const [password, setPassword] = useState("");
    const [error, setError] = useState(false);
    const [loading, setLoading] = useState(false);

    const handleSubmit = async (e) => {
        e.preventDefault();
        setLoading(true);
        setError(false);

        try {
            const res = await fetch("/api/login", {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify({ password }),
            });

            if (res.ok) {
                onLogin();
            } else {
                setError(true);
            }
        } catch (err) {
            setError(true);
        } finally {
            setLoading(false);
        }
    };

    return (
        <div className="container">
            <motion.div
                initial={{ opacity: 0, y: -20 }}
                animate={{ opacity: 1, y: 0 }}
            >
                <h1>NanettApp 🎁</h1>
            </motion.div>

            <form onSubmit={handleSubmit} style={{ width: '100%', maxWidth: '300px', display: 'flex', flexDirection: 'column', gap: '1rem' }}>
                <input
                    type="password"
                    placeholder="Parola Segreta..."
                    className="input-glass"
                    value={password}
                    onChange={(e) => setPassword(e.target.value)}
                />

                {error && (
                    <motion.p
                        initial={{ opacity: 0 }}
                        animate={{ opacity: 1 }}
                        style={{ color: 'var(--angry-color)', textAlign: 'center' }}
                    >
                        Riprova, amore! ❤️
                    </motion.p>
                )}

                <motion.button
                    whileHover={{ scale: 1.05 }}
                    whileTap={{ scale: 0.95 }}
                    className="btn"
                    style={{
                        background: 'var(--primary-color)',
                        color: 'white',
                        padding: '1rem',
                        borderRadius: '12px',
                        fontSize: '1.1rem',
                        boxShadow: '0 4px 15px rgba(255, 105, 180, 0.4)'
                    }}
                    disabled={loading}
                >
                    {loading ? "..." : "Entra"}
                </motion.button>
            </form>
        </div>
    );
}
