import {
  Html,
  Head,
  Body,
  Container,
  Text,
  Button,
  Hr,
  Preview,
} from "react-email";
import * as React from "react";

interface Props {
  userName: string;
  deckName: string;
  cardCount: number;
}

export default function WelcomeEmail({
  userName = "there",
  deckName = "90s Hits",
  cardCount = 30,
}: Props) {
  return (
    <Html lang="de">
      <Head />
      <Preview>Dein Deck „{deckName}" ist fertig 🎶</Preview>
      <Body
        style={{ backgroundColor: "#0a0a0a", fontFamily: "Georgia, serif" }}
      >
        <Container
          style={{ maxWidth: "560px", margin: "0 auto", padding: "48px 32px" }}
        >
          <Text
            style={{
              color: "#f5c842",
              letterSpacing: "0.25em",
              textTransform: "uppercase",
              fontSize: "13px",
            }}
          >
            ✦ Prompster
          </Text>
          <Text
            style={{
              color: "#f5f0e8",
              fontSize: "38px",
              fontWeight: 400,
              lineHeight: "1.2",
            }}
          >
            Dein Deck ist bereit, {userName}.
          </Text>
          <Text style={{ color: "#888", fontSize: "17px" }}>
            „{deckName}" — {cardCount} Karten, bereit zum Spielen.
          </Text>
          <Button
            href="https://prompster.app/decks"
            style={{
              backgroundColor: "#f5c842",
              color: "#0a0a0a",
              padding: "14px 32px",
              borderRadius: "6px",
              fontWeight: 700,
              fontSize: "14px",
              textTransform: "uppercase",
              letterSpacing: "0.08em",
            }}
          >
            Jetzt spielen →
          </Button>
          <Hr
            style={{ borderTop: "1px solid #1e1e1e", margin: "48px 0 24px" }}
          />
          <Text style={{ color: "#3a3a3a", fontSize: "12px" }}>
            Du bekommst diese Mail, weil du dich bei Prompster registriert hast.
          </Text>
        </Container>
      </Body>
    </Html>
  );
}
