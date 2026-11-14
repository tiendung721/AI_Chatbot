import Chat from "@/components/chat";
export default async function ChatPage({
  params,
}: {
  params: Promise<{ publicKey: string }>;
}) {
  const { publicKey } = await params;
  return (
    <main className="public-chat">
      <Chat publicKey={publicKey} />
    </main>
  );
}
