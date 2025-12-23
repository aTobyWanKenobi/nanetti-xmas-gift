import { useState, useEffect } from "react";
import { motion, AnimatePresence } from "framer-motion";

export default function PhotoDisplay({ emotionId, initialData, onComplete }) {
    const [data, setData] = useState(initialData || null);
    const [loading, setLoading] = useState(!initialData);
    const [countdown, setCountdown] = useState(null); // null, 3, 2, 1, 0

    useEffect(() => {
        if (initialData) return; // Skip fetch if we have data

        let ignore = false;

        fetch(`/api/draw/${emotionId}`)
            .then((res) => {
                if (!res.ok) throw new Error("Failed to load");
                return res.json();
            })
            .then((data) => {
                if (!ignore) {
                    setData(data);
                    setLoading(false);
                }
            })
            .catch((err) => {
                if (!ignore) {
                    console.error(err);
                    setLoading(false);
                }
            });

        return () => {
            ignore = true;
        };
    }, [emotionId, initialData]);

    useEffect(() => {
        if (!loading && data) {
            // Start 10s timer
            const timer = setTimeout(() => {
                startCountdown();
            }, 10000); // 10s

            return () => clearTimeout(timer);
        }
    }, [loading, data]);

    const startCountdown = () => {
        setCountdown(3);
    };

    useEffect(() => {
        if (countdown === null) return;

        if (countdown > 0) {
            const timer = setTimeout(() => setCountdown(countdown - 1), 1000);
            return () => clearTimeout(timer);
        } else if (countdown === 0) {
            // Trigger exit
            onComplete();
        }
    }, [countdown, onComplete]);

    if (loading) {
        return (
            <div className="container">
                <motion.div
                    animate={{ rotate: 360 }}
                    transition={{ repeat: Infinity, duration: 1, ease: "linear" }}
                    style={{
                        width: 50, height: 50,
                        border: '5px solid rgba(255,255,255,0.2)',
                        borderTopColor: 'var(--primary-color)',
                        borderRadius: '50%'
                    }}
                />
                <p>Scelgo un ricordo...</p>
            </div>
        );
    }

    return (
        <motion.div
            className="container"
            initial={{ opacity: 0, scale: 0.8, rotate: -5 }}
            animate={{ opacity: 1, scale: 1, rotate: 0 }}
            exit={{
                opacity: 0,
                scale: 0,
                rotate: 720,
                transition: { duration: 0.8, ease: "anticipate" }
            }}
            key="photo-container"
        >
            {/* Photo Card */}
            <div style={{
                background: 'white',
                padding: '12px 12px 60px 12px', /* Polaroid style */
                borderRadius: '4px',
                boxShadow: '0 10px 30px rgba(0,0,0,0.5)',
                transform: 'rotate(-2deg)',
                width: '90vw',
                maxWidth: '500px',
                position: 'relative'
            }}>
                {data?.photo_url ? (
                    <img
                        src={data.photo_url}
                        alt="Ricordo"
                        style={{
                            width: '100%',
                            height: 'auto',
                            aspectRatio: '1/1',
                            objectFit: 'cover',
                            borderRadius: '2px',
                            background: '#eee'
                        }}
                    />
                ) : (
                    <div style={{ width: '100%', aspectRatio: '1/1', background: '#eee', display: 'flex', alignItems: 'center', justifyContent: 'center', color: '#333' }}>
                        Nessuna foto trovata
                    </div>
                )}

                <div style={{
                    marginTop: '1.5rem',
                    fontFamily: 'Caveat, cursive, sans-serif', /* Handwriting font if avail */
                    fontSize: '1.6rem',
                    color: '#333',
                    textAlign: 'center',
                    lineHeight: '1.2'
                }}>
                    {data?.caption}
                </div>
            </div>

            {/* Countdown Overlay */}
            <AnimatePresence>
                {countdown !== null && countdown > 0 && (
                    <motion.div
                        initial={{ opacity: 0, scale: 0.5 }}
                        animate={{ opacity: 1, scale: 1.5 }}
                        exit={{ opacity: 0, scale: 2 }}
                        key={countdown}
                        style={{
                            position: 'absolute',
                            top: '50%',
                            left: '50%',
                            x: '-50%',
                            y: '-50%',
                            fontSize: '8rem',
                            fontWeight: 'bold',
                            color: 'white',
                            textShadow: '0 0 20px rgba(0,0,0,0.5)',
                            zIndex: 100,
                            pointerEvents: 'none'
                        }}
                    >
                        {countdown}
                    </motion.div>
                )}
            </AnimatePresence>
        </motion.div>
    );
}
