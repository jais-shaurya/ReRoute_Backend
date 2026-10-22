public class WalletSecurityQA {
    static int passed = 0;

    static void check(boolean condition, String name) {
        if (!condition) throw new AssertionError("FAILED: " + name);
        passed++;
        System.out.println("PASSED: " + name);
    }

    static void throwsError(Runnable action, Class<?> type, String name) {
        try {
            action.run();
            throw new AssertionError("FAILED: " + name);
        } catch (Throwable e) {
            if (!type.isInstance(e))
                throw new AssertionError("FAILED: " + name + " - wrong exception");
            passed++;
            System.out.println("PASSED: " + name);
        }
    }

    public static void main(String[] args) {
        DigitalWallet.Account alice =
            DigitalWallet.createAccount("A001", "1234", 10000);

        DigitalWallet.Account bob =
            DigitalWallet.createAccount("B001", "5678", 5000);

        // 1. Normal transaction
        DigitalWallet.deposit(alice, 1000);
        check(DigitalWallet.verifyBalance(alice, 11000), "Normal deposit");

        // 2. Transfer
        DigitalWallet.transfer(alice, bob, 1000, "1234");
        check(DigitalWallet.verifyBalance(alice, 10000), "Money transfer");

        // 3. Insufficient balance
        throwsError(
            () -> DigitalWallet.withdraw(alice, 20000, "1234"),
            IllegalStateException.class,
            "Insufficient balance"
        );

        // 4. Daily transaction limit
        throwsError(
            () -> DigitalWallet.withdraw(alice, 60000, "1234"),
            IllegalArgumentException.class,
            "Daily transaction limit"
        );

        // 5. Negative amount
        throwsError(
            () -> DigitalWallet.deposit(alice, -100),
            IllegalArgumentException.class,
            "Negative amount"
        );

        // 6. Invalid PIN
        throwsError(
            () -> DigitalWallet.withdraw(alice, 100, "9999"),
            SecurityException.class,
            "Invalid PIN"
        );

        // 7. Multiple failed PIN attempts
        for (int i = 0; i < 3; i++) {
            try {
                DigitalWallet.withdraw(alice, 100, "0000");
            } catch (SecurityException ignored) {}
        }
        check(alice.failedPins >= 3, "Multiple failed PINs");

        // 8. Suspicious large transaction
        DigitalWallet.Account suspicious =
            DigitalWallet.createAccount("A002", "1111", 50000);

        DigitalWallet.transfer(suspicious, bob, 25000, "1111");

        check(
            DigitalWallet.transactionHistory(suspicious)
                .stream()
                .anyMatch(s -> s.startsWith("FRAUD_FLAG")),
            "Suspicious large transaction"
        );

        // 9. Transaction history
        check(
            !DigitalWallet.transactionHistory(alice).isEmpty(),
            "Transaction history"
        );

        // 10. Account creation
        check(
            DigitalWallet.createAccount("A003", "2222", 100).balance == 100,
            "Account creation"
        );

        // 11. Invalid PIN length
        throwsError(
            () -> DigitalWallet.createAccount("A004", "12", 100),
            IllegalArgumentException.class,
            "Invalid PIN length"
        );

        // 12. Zero amount
        throwsError(
            () -> DigitalWallet.deposit(alice, 0),
            IllegalArgumentException.class,
            "Zero amount"
        );

        // 13. Balance verification
        check(DigitalWallet.verifyBalance(bob, 6000), "Balance verification");

        // 14. Duplicate transaction simulation
        double before = bob.balance;
        DigitalWallet.transfer(alice, bob, 100, "1234");
        check(bob.balance == before + 100, "Duplicate transaction scenario");

        // 15. Concurrent-style sequential transactions
        DigitalWallet.transfer(alice, bob, 100, "1234");
        DigitalWallet.transfer(alice, bob, 100, "1234");
        check(bob.balance == before + 300, "Concurrent transaction scenario");

        System.out.println("--------------------------------");
        System.out.println("TOTAL PASSED: " + passed);
        System.out.println("ALL WALLET QA TESTS PASSED");
    }
}
