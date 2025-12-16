import { motion } from "framer-motion";

const emotions = [
    { id: "happy", label: "Felice", color: "var(--happy-color)", emoji: "😊" },
    { id: "romantic", label: "Romantica", color: "var(--romantic-color)", emoji: "💖" },
    { id: "sad", label: "Triste", color: "var(--sad-color)", emoji: "😢" },
    { id: "angry", label: "Arrabbiata", color: "var(--angry-color)", emoji: "😡" },
];

export default function EmotionSelector({ onSelect }) {
    return (
        <div className="container" style={{ maxWidth: '100%' }}>
            <motion.div
                initial={{ opacity: 0, y: -20 }}
                animate={{ opacity: 1, y: 0 }}
                transition={{ duration: 0.5 }}
            >
                <h1 style={{ fontSize: '2.5rem', marginBottom: '0.5rem' }}>NanettApp 🎁</h1>
                <h2 style={{ fontSize: '1.5rem', fontWeight: '400', marginBottom: '2rem', textAlign: 'center' }}>Come ti senti adesso?</h2>
            </motion.div>

            <div style={{
                display: 'grid',
                gridTemplateColumns: '1fr 1fr',
                gap: '1.5rem',
                width: '100%'
            }}>
                {emotions.map((emotion, index) => (
                    <motion.button
                        key={emotion.id}
                        onClick={() => onSelect(emotion.id)}
                        className="btn"
                        style={{
                            backgroundColor: emotion.color,
                            height: '140px',
                            borderRadius: '24px',
                            fontSize: '1.2rem',
                            color: '#333',
                            display: 'flex',
                            flexDirection: 'column',
                            justifyContent: 'center',
                            alignItems: 'center',
                            position: 'relative',
                            overflow: 'hidden',
                            // 3D Effect
                            border: 'none',
                            borderBottom: '8px solid rgba(0,0,0,0.2)',
                            boxShadow: '0 10px 20px rgba(0,0,0,0.2)',
                        }}
                        initial={{ opacity: 0, scale: 0.8 }}
                        animate={{ opacity: 1, scale: 1 }}
                        transition={{ delay: index * 0.1, type: "spring" }}
                        whileHover={{
                            scale: 1.05,
                            y: -5,
                            filter: 'brightness(1.1)'
                        }}
                        whileTap={{
                            scale: 0.95,
                            y: 4,
                            borderBottomWidth: '2px',
                            boxShadow: '0 2px 10px rgba(0,0,0,0.1)'
                        }}
                    >
                        <span style={{ fontSize: '3rem', marginBottom: '0.5rem' }}>{emotion.emoji}</span>
                        <span style={{ fontWeight: '800' }}>{emotion.label}</span>
                    </motion.button>
                ))}
            </div>
        </div>
    );
}
